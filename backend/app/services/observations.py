from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.database import next_observation_sequence_value
from app.models import (
    AuditReport,
    Observation,
    ObservationHistory,
    ObservationResponse,
    ObservationSeverity,
    ObservationStatus,
    ResponseType,
    User,
    UserRole,
)
from app.schemas import (
    DashboardStats,
    ObservationAssign,
    ObservationCreate,
    ObservationResponseCreate,
    ObservationUpdate,
    ObservationVerify,
)
from app.services.access import (
    apply_observation_scope,
    can_access_scope,
    load_user_access,
    require_scope,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ObservationService:
    def __init__(self, db: Session):
        self.db = db

    def _actor(self, actor: User) -> User:
        return load_user_access(self.db, actor)

    def _next_observation_number(self) -> str:
        year = _now().year
        seq = next_observation_sequence_value(self.db)
        if seq is not None:
            return f"OBS-{year}-{int(seq):05d}"
        count = self.db.query(func.count(Observation.id)).scalar() or 0
        return f"OBS-{year}-{count + 1:05d}"

    def _history(
        self,
        observation: Observation,
        actor_id: int,
        action: str,
        from_status: Optional[str],
        to_status: Optional[str],
        notes: Optional[str] = None,
    ) -> None:
        self.db.add(
            ObservationHistory(
                observation_id=observation.id,
                actor_id=actor_id,
                action=action,
                from_status=from_status,
                to_status=to_status,
                notes=notes,
            )
        )

    def create(self, data: ObservationCreate, actor: User) -> Observation:
        actor = self._actor(actor)
        if actor.role not in {UserRole.ADMIN.value, UserRole.CENTRAL_TEAM.value, UserRole.AUDITOR.value}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to create observations")
        report = self.db.query(AuditReport).filter(AuditReport.id == data.report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        require_scope(actor, report.region, report.segment, action="create observations on")

        region = data.region.value if data.region else report.region
        segment = data.segment.value if data.segment else report.segment
        require_scope(actor, region, segment, action="create observations in")

        obs = Observation(
            report_id=data.report_id,
            observation_number=self._next_observation_number(),
            title=data.title,
            description=data.description,
            category=data.category,
            region=region,
            segment=segment,
            severity=data.severity.value,
            recommendation=data.recommendation,
            status=ObservationStatus.DRAFT.value,
            created_by_id=actor.id,
        )
        self.db.add(obs)
        self.db.flush()
        self._history(obs, actor.id, "CREATED", None, ObservationStatus.DRAFT.value)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def submit_for_review(self, observation_id: int, actor: User) -> Observation:
        actor = self._actor(actor)
        obs = self.get(observation_id, actor)
        if obs.status != ObservationStatus.DRAFT.value:
            raise HTTPException(status_code=400, detail="Only draft observations can be submitted")
        if actor.role not in {UserRole.ADMIN.value, UserRole.CENTRAL_TEAM.value, UserRole.AUDITOR.value}:
            raise HTTPException(status_code=403, detail="Not allowed")
        prev = obs.status
        obs.status = ObservationStatus.PENDING_REVIEW.value
        self._history(obs, actor.id, "SUBMITTED_FOR_REVIEW", prev, obs.status)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def assign(self, observation_id: int, data: ObservationAssign, actor: User) -> Observation:
        actor = self._actor(actor)
        if actor.role not in {UserRole.ADMIN.value, UserRole.CENTRAL_TEAM.value}:
            raise HTTPException(status_code=403, detail="Only central team can assign")
        obs = self.get(observation_id, actor)
        if obs.status not in {ObservationStatus.PENDING_REVIEW.value, ObservationStatus.ASSIGNED.value}:
            raise HTTPException(status_code=400, detail="Observation not ready for assignment")
        owner = self.db.query(User).filter(User.id == data.owner_id, User.is_active.is_(True)).first()
        if not owner or owner.role not in {UserRole.PROCESS_OWNER.value, UserRole.ADMIN.value}:
            raise HTTPException(status_code=400, detail="Invalid process owner")
        owner = load_user_access(self.db, owner)
        if owner.role != UserRole.ADMIN.value and not can_access_scope(owner, obs.region, obs.segment):
            raise HTTPException(
                status_code=400,
                detail="Process owner is not authorized for this observation region/segment",
            )
        prev = obs.status
        obs.owner_id = owner.id
        obs.assigned_by_id = actor.id
        obs.due_date = data.due_date
        obs.status = ObservationStatus.ASSIGNED.value
        self._history(obs, actor.id, "ASSIGNED", prev, obs.status, data.notes)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def respond(self, observation_id: int, data: ObservationResponseCreate, actor: User) -> Observation:
        actor = self._actor(actor)
        obs = self.get(observation_id, actor)
        if actor.role not in {UserRole.PROCESS_OWNER.value, UserRole.ADMIN.value}:
            raise HTTPException(status_code=403, detail="Only process owners can respond")
        if obs.owner_id != actor.id and actor.role != UserRole.ADMIN.value:
            raise HTTPException(status_code=403, detail="Not assigned to you")
        if obs.status not in {ObservationStatus.ASSIGNED.value, ObservationStatus.IN_PROGRESS.value}:
            raise HTTPException(status_code=400, detail="Observation not open for response")
        if data.response_type in {ResponseType.NEED_MORE_TIME, ResponseType.COMMITTED_TIMELINE} and not data.committed_date:
            raise HTTPException(status_code=400, detail="committed_date required for this response type")

        response = ObservationResponse(
            observation_id=obs.id,
            responder_id=actor.id,
            response_type=data.response_type.value,
            comments=data.comments,
            committed_date=data.committed_date,
        )
        self.db.add(response)
        prev = obs.status
        if data.response_type == ResponseType.RESOLVED:
            obs.status = ObservationStatus.PENDING_VERIFICATION.value
            action = "RESPONSE_RESOLVED"
        else:
            obs.status = ObservationStatus.IN_PROGRESS.value
            if data.committed_date:
                obs.due_date = data.committed_date
            action = f"RESPONSE_{data.response_type.value}"
        self._history(obs, actor.id, action, prev, obs.status, data.comments)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def verify(self, observation_id: int, data: ObservationVerify, actor: User) -> Observation:
        actor = self._actor(actor)
        if actor.role not in {UserRole.ADMIN.value, UserRole.CENTRAL_TEAM.value}:
            raise HTTPException(status_code=403, detail="Only central team can verify")
        obs = self.get(observation_id, actor)
        if obs.status != ObservationStatus.PENDING_VERIFICATION.value:
            raise HTTPException(status_code=400, detail="Observation not pending verification")
        prev = obs.status
        if data.approved:
            obs.status = ObservationStatus.CLOSED.value
            obs.closed_at = _now()
            obs.closed_by_id = actor.id
            action = "VERIFIED_CLOSED"
        else:
            obs.status = ObservationStatus.ASSIGNED.value
            action = "VERIFICATION_REJECTED"
        self._history(obs, actor.id, action, prev, obs.status, data.notes)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def update(self, observation_id: int, data: ObservationUpdate, actor: User) -> Observation:
        actor = self._actor(actor)
        obs = self.get(observation_id, actor)
        if actor.role not in {UserRole.ADMIN.value, UserRole.CENTRAL_TEAM.value, UserRole.AUDITOR.value}:
            raise HTTPException(status_code=403, detail="Not allowed")
        if obs.status not in {ObservationStatus.DRAFT.value, ObservationStatus.PENDING_REVIEW.value}:
            raise HTTPException(status_code=400, detail="Cannot edit observation in current status")
        payload = data.model_dump(exclude_unset=True)
        if "region" in payload and payload["region"] is not None:
            payload["region"] = payload["region"].value if hasattr(payload["region"], "value") else payload["region"]
        if "segment" in payload and payload["segment"] is not None:
            payload["segment"] = payload["segment"].value if hasattr(payload["segment"], "value") else payload["segment"]
        if "severity" in payload and payload["severity"] is not None:
            payload["severity"] = payload["severity"].value if hasattr(payload["severity"], "value") else payload["severity"]
        next_region = payload.get("region", obs.region)
        next_segment = payload.get("segment", obs.segment)
        require_scope(actor, next_region, next_segment, action="update observations in")
        for field, value in payload.items():
            setattr(obs, field, value)
        self._history(obs, actor.id, "UPDATED", obs.status, obs.status)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def get(self, observation_id: int, actor: Optional[User] = None) -> Observation:
        obs = (
            self.db.query(Observation)
            .options(
                joinedload(Observation.responses),
                joinedload(Observation.history),
                joinedload(Observation.owner),
                joinedload(Observation.report),
            )
            .filter(Observation.id == observation_id)
            .first()
        )
        if not obs:
            raise HTTPException(status_code=404, detail="Observation not found")
        if actor is not None:
            actor = self._actor(actor)
            if not can_access_scope(actor, obs.region, obs.segment):
                raise HTTPException(status_code=403, detail="Not allowed to view this observation")
            if actor.role == UserRole.PROCESS_OWNER.value and obs.owner_id != actor.id:
                raise HTTPException(status_code=403, detail="Not assigned to you")
        return obs

    def list(
        self,
        actor: User,
        status_filter: Optional[str] = None,
        severity: Optional[str] = None,
        owner_id: Optional[int] = None,
        report_id: Optional[int] = None,
        region: Optional[str] = None,
        segment: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Observation]:
        actor = self._actor(actor)
        q = self.db.query(Observation).options(joinedload(Observation.owner), joinedload(Observation.report))
        q = apply_observation_scope(q, actor, Observation)
        if actor.role == UserRole.PROCESS_OWNER.value:
            q = q.filter(Observation.owner_id == actor.id)
        if status_filter:
            q = q.filter(Observation.status == status_filter)
        if severity:
            q = q.filter(Observation.severity == severity)
        if owner_id:
            q = q.filter(Observation.owner_id == owner_id)
        if report_id:
            q = q.filter(Observation.report_id == report_id)
        if region:
            q = q.filter(Observation.region == region)
        if segment:
            q = q.filter(Observation.segment == segment)
        return q.order_by(Observation.created_at.desc()).offset(skip).limit(limit).all()

    def dashboard(self, actor: User) -> DashboardStats:
        actor = self._actor(actor)
        q = self.db.query(Observation)
        q = apply_observation_scope(q, actor, Observation)
        if actor.role == UserRole.PROCESS_OWNER.value:
            q = q.filter(Observation.owner_id == actor.id)
        rows = q.all()
        by_status = {s.value: 0 for s in ObservationStatus}
        by_severity = {s.value: 0 for s in ObservationSeverity}
        by_region: dict[str, int] = {}
        by_segment: dict[str, int] = {}
        overdue = 0
        now = _now()
        for obs in rows:
            by_status[obs.status] = by_status.get(obs.status, 0) + 1
            by_severity[obs.severity] = by_severity.get(obs.severity, 0) + 1
            by_region[obs.region] = by_region.get(obs.region, 0) + 1
            by_segment[obs.segment] = by_segment.get(obs.segment, 0) + 1
            if (
                obs.due_date
                and obs.status not in {ObservationStatus.CLOSED.value, ObservationStatus.REJECTED.value}
                and obs.due_date.replace(tzinfo=timezone.utc) < now
            ):
                overdue += 1
        return DashboardStats(
            total=len(rows),
            draft=by_status[ObservationStatus.DRAFT.value],
            pending_review=by_status[ObservationStatus.PENDING_REVIEW.value],
            assigned=by_status[ObservationStatus.ASSIGNED.value],
            in_progress=by_status[ObservationStatus.IN_PROGRESS.value],
            pending_verification=by_status[ObservationStatus.PENDING_VERIFICATION.value],
            closed=by_status[ObservationStatus.CLOSED.value],
            rejected=by_status[ObservationStatus.REJECTED.value],
            by_severity=by_severity,
            by_region=by_region,
            by_segment=by_segment,
            overdue=overdue,
        )
