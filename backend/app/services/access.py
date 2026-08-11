"""Region and segment access-control helpers."""

from __future__ import annotations

from typing import Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy import false
from sqlalchemy.orm import Query, Session, joinedload

from app.models import AuditSegment, Region, User, UserRegion, UserRole, UserSegment


ALL_REGIONS = [r.value for r in Region]
ALL_SEGMENTS = [s.value for s in AuditSegment]


def load_user_access(db: Session, user: User) -> User:
    """Ensure region/segment collections are loaded."""
    if user.id is None:
        return user
    return (
        db.query(User)
        .options(joinedload(User.region_access), joinedload(User.segment_access))
        .filter(User.id == user.id)
        .one()
    )


def is_global_admin(user: User) -> bool:
    return (user.role or "").upper() == UserRole.ADMIN.value


def assigned_regions(user: User) -> set[str]:
    return {r.region for r in (user.region_access or [])}


def assigned_segments(user: User) -> set[str]:
    return {s.segment for s in (user.segment_access or [])}


def effective_regions(user: User) -> Optional[set[str]]:
    """None means unrestricted (admin). Empty set means no regional access."""
    if is_global_admin(user):
        return None
    return assigned_regions(user)


def effective_segments(user: User) -> Optional[set[str]]:
    if is_global_admin(user):
        return None
    return assigned_segments(user)


def can_access_scope(user: User, region: str, segment: str) -> bool:
    regions = effective_regions(user)
    segments = effective_segments(user)
    if regions is not None and region not in regions:
        return False
    if segments is not None and segment not in segments:
        return False
    # Non-admins with zero assignments cannot see anything
    if regions is not None and not regions:
        return False
    if segments is not None and not segments:
        return False
    return True


def require_scope(user: User, region: str, segment: str, action: str = "access") -> None:
    if not can_access_scope(user, region, segment):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not allowed to {action} data for region={region} segment={segment}",
        )


def apply_observation_scope(query: Query, user: User, Observation) -> Query:
    regions = effective_regions(user)
    segments = effective_segments(user)
    if regions is not None:
        if not regions:
            return query.filter(false())
        query = query.filter(Observation.region.in_(regions))
    if segments is not None:
        if not segments:
            return query.filter(false())
        query = query.filter(Observation.segment.in_(segments))
    return query


def apply_report_scope(query: Query, user: User, AuditReport) -> Query:
    regions = effective_regions(user)
    segments = effective_segments(user)
    if regions is not None:
        if not regions:
            return query.filter(false())
        query = query.filter(AuditReport.region.in_(regions))
    if segments is not None:
        if not segments:
            return query.filter(false())
        query = query.filter(AuditReport.segment.in_(segments))
    return query


def set_user_regions(db: Session, user: User, regions: Iterable[str]) -> None:
    wanted = {Region(r).value for r in regions}
    user.region_access.clear()
    db.flush()
    for region in sorted(wanted):
        user.region_access.append(UserRegion(region=region))


def set_user_segments(db: Session, user: User, segments: Iterable[str]) -> None:
    wanted = {AuditSegment(s).value for s in segments}
    user.segment_access.clear()
    db.flush()
    for segment in sorted(wanted):
        user.segment_access.append(UserSegment(segment=segment))
