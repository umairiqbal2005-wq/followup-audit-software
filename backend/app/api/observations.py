from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import (
    DashboardStats,
    ObservationAssign,
    ObservationCreate,
    ObservationDetail,
    ObservationHistoryOut,
    ObservationOut,
    ObservationResponseCreate,
    ObservationResponseOut,
    ObservationUpdate,
    ObservationVerify,
)
from app.services.observations import ObservationService

router = APIRouter(prefix="/observations", tags=["observations"])


def _to_out(obs) -> ObservationOut:
    data = ObservationOut.model_validate(obs)
    data.owner_name = obs.owner.full_name if obs.owner else None
    data.report_title = obs.report.title if obs.report else None
    return data


def _to_detail(obs) -> ObservationDetail:
    base = _to_out(obs)
    return ObservationDetail(
        **base.model_dump(),
        responses=[ObservationResponseOut.model_validate(r) for r in obs.responses],
        history=[ObservationHistoryOut.model_validate(h) for h in obs.history],
    )


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    return ObservationService(db).dashboard(user)


@router.get("", response_model=list[ObservationOut])
def list_observations(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    status: Optional[str] = None,
    severity: Optional[str] = None,
    owner_id: Optional[int] = None,
    report_id: Optional[int] = None,
    region: Optional[str] = None,
    segment: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    rows = ObservationService(db).list(
        user,
        status_filter=status,
        severity=severity,
        owner_id=owner_id,
        report_id=report_id,
        region=region,
        segment=segment,
        skip=skip,
        limit=limit,
    )
    return [_to_out(o) for o in rows]


@router.post("", response_model=ObservationOut, status_code=201)
def create_observation(
    payload: ObservationCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    service = ObservationService(db)
    obs = service.create(payload, user)
    return _to_out(service.get(obs.id, user))


@router.get("/{observation_id}", response_model=ObservationDetail)
def get_observation(
    observation_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    return _to_detail(ObservationService(db).get(observation_id, user))


@router.patch("/{observation_id}", response_model=ObservationOut)
def update_observation(
    observation_id: int,
    payload: ObservationUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    service = ObservationService(db)
    obs = service.update(observation_id, payload, user)
    return _to_out(service.get(obs.id, user))


@router.post("/{observation_id}/submit", response_model=ObservationOut)
def submit_observation(
    observation_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    service = ObservationService(db)
    obs = service.submit_for_review(observation_id, user)
    return _to_out(service.get(obs.id, user))


@router.post("/{observation_id}/assign", response_model=ObservationOut)
def assign_observation(
    observation_id: int,
    payload: ObservationAssign,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    service = ObservationService(db)
    obs = service.assign(observation_id, payload, user)
    return _to_out(service.get(obs.id, user))


@router.post("/{observation_id}/respond", response_model=ObservationOut)
def respond_observation(
    observation_id: int,
    payload: ObservationResponseCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    service = ObservationService(db)
    obs = service.respond(observation_id, payload, user)
    return _to_out(service.get(obs.id, user))


@router.post("/{observation_id}/verify", response_model=ObservationOut)
def verify_observation(
    observation_id: int,
    payload: ObservationVerify,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    service = ObservationService(db)
    obs = service.verify(observation_id, payload, user)
    return _to_out(service.get(obs.id, user))
