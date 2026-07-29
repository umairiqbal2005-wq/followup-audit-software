from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.core.security import hash_password
from app.models import User, UserRole
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserOut, UserUpdate
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    service = AuthService(db)
    user = service.authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return service.issue_token(user)


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user


users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("", response_model=list[UserOut])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CENTRAL_TEAM))],
    skip: int = 0,
    limit: int = 100,
    role: str | None = None,
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    return q.order_by(User.full_name).offset(skip).limit(limit).all()


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
    db.commit()
    db.refresh(user)
    return user


@users_router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        pwd = data.pop("password")
        if pwd:
            user.hashed_password = hash_password(pwd)
    if "role" in data and data["role"] is not None:
        data["role"] = data["role"].value if hasattr(data["role"], "value") else data["role"]
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user
