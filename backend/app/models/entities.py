from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="VIEWER")
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ldap_dn: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owned_observations: Mapped[list["Observation"]] = relationship(
        "Observation", back_populates="owner", foreign_keys="Observation.owner_id"
    )
    responses: Mapped[list["ObservationResponse"]] = relationship(
        "ObservationResponse", back_populates="responder"
    )


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    report_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    audit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    uploaded_by: Mapped["User"] = relationship("User")
    observations: Mapped[list["Observation"]] = relationship(
        "Observation", back_populates="report", cascade="all, delete-orphan"
    )


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("audit_reports.id"), nullable=False, index=True)
    observation_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="MEDIUM")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT", index=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    assigned_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    report: Mapped["AuditReport"] = relationship("AuditReport", back_populates="observations")
    owner: Mapped["User | None"] = relationship(
        "User", back_populates="owned_observations", foreign_keys=[owner_id]
    )
    assigned_by: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_by_id])
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
    closed_by: Mapped["User | None"] = relationship("User", foreign_keys=[closed_by_id])
    responses: Mapped[list["ObservationResponse"]] = relationship(
        "ObservationResponse", back_populates="observation", cascade="all, delete-orphan"
    )
    history: Mapped[list["ObservationHistory"]] = relationship(
        "ObservationHistory", back_populates="observation", cascade="all, delete-orphan"
    )


class ObservationResponse(Base):
    __tablename__ = "observation_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_id: Mapped[int] = mapped_column(ForeignKey("observations.id"), nullable=False, index=True)
    responder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    response_type: Mapped[str] = mapped_column(String(50), nullable=False)
    comments: Mapped[str] = mapped_column(Text, nullable=False)
    committed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_file: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    observation: Mapped["Observation"] = relationship("Observation", back_populates="responses")
    responder: Mapped["User"] = relationship("User", back_populates="responses")


class ObservationHistory(Base):
    __tablename__ = "observation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_id: Mapped[int] = mapped_column(ForeignKey("observations.id"), nullable=False, index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    observation: Mapped["Observation"] = relationship("Observation", back_populates="history")
    actor: Mapped["User"] = relationship("User")
