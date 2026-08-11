from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.core.security import hash_password
from app.models import AuditSegment, Region, User, UserRole
from app.schemas import AccessCatalog, LoginRequest, TokenResponse, UserCreate, UserOut, UserUpdate
from app.services.access import ALL_REGIONS, ALL_SEGMENTS, set_user_regions, set_user_segments
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    role_value = (user.role or UserRole.VIEWER.value).upper()
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=UserRole(role_value),
        department=user.department,
        is_active=user.is_active,
        created_at=user.created_at,
        regions=sorted({r.region for r in user.region_access or []}),
        segments=sorted({s.segment for s in user.segment_access or []}),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    service = AuthService(db)
    username = (payload.username or "").strip()
    password = (payload.password or "").strip()
    user = service.authenticate(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password. Use admin / demo123 (or umair / demo123).",
        )
    return service.issue_token(user)


@router.get("/demo-logins")
def demo_logins(db: Annotated[Session, Depends(get_db)]):
    """Development helper: shows which demo accounts exist and are active."""
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.should_bootstrap_dev_users:
        return {"enabled": False, "users": []}
    # Ensure accounts exist before listing
    AuthService(db).ensure_dev_admin()
    rows = (
        db.query(User)
        .filter(User.username.in_(["admin", "umair", "khurrum", "central1", "owner1"]))
        .order_by(User.username)
        .all()
    )
    return {
        "enabled": True,
        "password": settings.dev_admin_password,
        "users": [{"username": u.username, "role": u.role, "active": u.is_active} for u in rows],
    }


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    loaded = (
        db.query(User)
        .options(joinedload(User.region_access), joinedload(User.segment_access))
        .filter(User.id == user.id)
        .one()
    )
    return _user_out(loaded)


@router.get("/access-catalog", response_model=AccessCatalog)
def access_catalog(_: Annotated[User, Depends(get_current_user)]):
    return AccessCatalog(
        roles=[r.value for r in UserRole],
        regions=ALL_REGIONS,
        segments=ALL_SEGMENTS,
    )


users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("", response_model=list[UserOut])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CENTRAL_TEAM))],
    skip: int = 0,
    limit: int = 100,
    role: str | None = None,
    region: str | None = None,
):
    q = db.query(User).options(joinedload(User.region_access), joinedload(User.segment_access))
    if role:
        q = q.filter(User.role == role)
    users = q.order_by(User.full_name).offset(skip).limit(limit).all()
    if region:
        users = [u for u in users if region in {r.region for r in u.region_access}]
    return [_user_out(u) for u in users]


@users_router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
):
    if db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists")
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role.value,
        department=payload.department,
        hashed_password=hash_password(payload.password) if payload.password else None,
        is_active=True,
    )
    db.add(user)
    db.flush()
    set_user_regions(db, user, [r.value for r in payload.regions])
    set_user_segments(db, user, [s.value for s in payload.segments])
    db.commit()
    db.refresh(user)
    user = (
        db.query(User)
        .options(joinedload(User.region_access), joinedload(User.segment_access))
        .filter(User.id == user.id)
        .one()
    )
    return _user_out(user)


@users_router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
):
    user = (
        db.query(User)
        .options(joinedload(User.region_access), joinedload(User.segment_access))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    regions = data.pop("regions", None)
    segments = data.pop("segments", None)
    if "password" in data:
        pwd = data.pop("password")
        if pwd:
            user.hashed_password = hash_password(pwd)
    if "role" in data and data["role"] is not None:
        data["role"] = data["role"].value if hasattr(data["role"], "value") else data["role"]
    for key, value in data.items():
        setattr(user, key, value)
    if regions is not None:
        set_user_regions(db, user, [Region(r).value if not isinstance(r, str) else r for r in regions])
    if segments is not None:
        set_user_segments(db, user, [AuditSegment(s).value if not isinstance(s, str) else s for s in segments])
    db.commit()
    user = (
        db.query(User)
        .options(joinedload(User.region_access), joinedload(User.segment_access))
        .filter(User.id == user_id)
        .one()
    )
    return _user_out(user)
