from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ObservationSeverity, ObservationStatus, ResponseType, UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role: UserRole
    department: Optional[str] = None


class UserCreate(UserBase):
    password: Optional[str] = Field(default=None, min_length=8)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8)


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime


class AuditReportCreate(BaseModel):
    title: str
    report_number: str
    description: Optional[str] = None
    audit_date: Optional[datetime] = None


class AuditReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    report_number: str
    description: Optional[str] = None
    file_name: Optional[str] = None
    uploaded_by_id: int
    audit_date: Optional[datetime] = None
    created_at: datetime
    observation_count: int = 0


class ObservationCreate(BaseModel):
    report_id: int
    title: str
    description: str
    category: Optional[str] = None
    severity: ObservationSeverity = ObservationSeverity.MEDIUM
    recommendation: Optional[str] = None


class ObservationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[ObservationSeverity] = None
    recommendation: Optional[str] = None


class ObservationAssign(BaseModel):
    owner_id: int
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class ObservationResponseCreate(BaseModel):
    response_type: ResponseType
    comments: str
    committed_date: Optional[datetime] = None


class ObservationVerify(BaseModel):
    approved: bool
    notes: Optional[str] = None


class ObservationResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    observation_id: int
    responder_id: int
    response_type: str
    comments: str
    committed_date: Optional[datetime] = None
    evidence_file: Optional[str] = None
    created_at: datetime


class ObservationHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    notes: Optional[str] = None
    actor_id: int
    created_at: datetime


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    observation_number: str
    title: str
    description: str
    category: Optional[str] = None
    severity: str
    status: str
    recommendation: Optional[str] = None
    owner_id: Optional[int] = None
    assigned_by_id: Optional[int] = None
    due_date: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    owner_name: Optional[str] = None
    report_title: Optional[str] = None


class ObservationDetail(ObservationOut):
    responses: list[ObservationResponseOut] = []
    history: list[ObservationHistoryOut] = []


class DashboardStats(BaseModel):
    total: int
    draft: int
    pending_review: int
    assigned: int
    in_progress: int
    pending_verification: int
    closed: int
    rejected: int
    by_severity: dict[str, int]
    overdue: int
