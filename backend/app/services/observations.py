from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.database import next_observation_sequence_value
from app.models import (
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


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ObservationService:
    def __init__(self, db: Session):
        self.db = db

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
        if actor.role not in {UserRole.ADMIN.value, UserRole.CENTRAL_TEAM.value, UserRole.AUDITOR.value}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to create observations")
        obs = Observation(
            report_id=data.report_id,
            observation_number=self._next_observation_number(),
            title=data.title,
            description=data.description,
            category=data.category,
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
        obs = self.get(observation_id)
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
        if actor.role not in {UserRole.ADMIN.value, UserRole.CENTRAL_TEAM.value}:
            raise HTTPException(status_code=403, detail="Only central team can assign")
        obs = self.get(observation_id)
        if obs.status not in {ObservationStatus.PENDING_REVIEW.value, ObservationStatus.ASSIGNED.value}:
            raise HTTPException(status_code=400, detail="Observation not ready for assignment")
        owner = self.db.query(User).filter(User.id == data.owner_id, User.is_active.is_(True)).first()
        if not owner or owner.role not in {UserRole.PROCESS_OWNER.value, UserRole.ADMIN.value}:
            raise HTTPException(status_code=400, detail="Invalid process owner")
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
        obs = self.get(observation_id)
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
        if actor.role not in {UserRole.ADMIN.value, UserRole.CENTRAL_TEAM.value}:
            raise HTTPException(status_code=403, detail="Only central team can verify")
        obs = self.get(observation_id)
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
        obs = self.get(observation_id)
        if actor.role not in {UserRole.ADMIN.value, UserRole.CENTRAL_TEAM.value, UserRole.AUDITOR.value}:
            raise HTTPException(status_code=403, detail="Not allowed")
        if obs.status not in {ObservationStatus.DRAFT.value, ObservationStatus.PENDING_REVIEW.value}:
            raise HTTPException(status_code=400, detail="Cannot edit observation in current status")
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "severity" and value is not None:
                setattr(obs, field, value.value if hasattr(value, "value") else value)
            else:
                setattr(obs, field, value)
        self._history(obs, actor.id, "UPDATED", obs.status, obs.status)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def get(self, observation_id: int) -> Observation:
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
        return obs

    def list(
        self,
        actor: User,
        status_filter: Optional[str] = None,
        severity: Optional[str] = None,
        owner_id: Optional[int] = None,
        report_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Observation]:
        q = self.db.query(Observation).options(joinedload(Observation.owner), joinedload(Observation.report))
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
        return q.order_by(Observation.created_at.desc()).offset(skip).limit(limit).all()

    def dashboard(self, actor: User) -> DashboardStats:
        q = self.db.query(Observation)
        if actor.role == UserRole.PROCESS_OWNER.value:
            q = q.filter(Observation.owner_id == actor.id)
        rows = q.all()
        by_status = {s.value: 0 for s in ObservationStatus}
        by_severity = {s.value: 0 for s in ObservationSeverity}
        overdue = 0
        now = _now()
        for obs in rows:
            by_status[obs.status] = by_status.get(obs.status, 0) + 1
            by_severity[obs.severity] = by_severity.get(obs.severity, 0) + 1
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
            overdue=overdue,
        )
