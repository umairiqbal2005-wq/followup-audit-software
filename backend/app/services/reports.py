import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AuditReport, User, UserRole
from app.schemas import AuditReportCreate


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        Path(self.settings.upload_dir).mkdir(parents=True, exist_ok=True)

    def create(self, data: AuditReportCreate, actor: User, file: Optional[UploadFile] = None) -> AuditReport:
        if actor.role not in {UserRole.ADMIN.value, UserRole.CENTRAL_TEAM.value, UserRole.AUDITOR.value}:
            raise HTTPException(status_code=403, detail="Not allowed to upload reports")
        existing = self.db.query(AuditReport).filter(AuditReport.report_number == data.report_number).first()
        if existing:
            raise HTTPException(status_code=400, detail="Report number already exists")

        file_name = None
        file_path = None
        if file and file.filename:
            ext = Path(file.filename).suffix.lower()
            if ext not in {".pdf", ".xlsx", ".xls", ".csv"}:
                raise HTTPException(status_code=400, detail="Only PDF/Excel/CSV files allowed")
            content = file.file.read()
            max_bytes = self.settings.max_upload_mb * 1024 * 1024
            if len(content) > max_bytes:
                raise HTTPException(status_code=400, detail="File too large")
            stored = f"{uuid.uuid4().hex}{ext}"
            dest = os.path.join(self.settings.upload_dir, stored)
            with open(dest, "wb") as fh:
                fh.write(content)
            file_name = file.filename
            file_path = dest

        report = AuditReport(
            title=data.title,
            report_number=data.report_number,
            description=data.description,
            audit_date=data.audit_date,
            uploaded_by_id=actor.id,
            file_name=file_name,
            file_path=file_path,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def list(self, skip: int = 0, limit: int = 50) -> list[AuditReport]:
        return self.db.query(AuditReport).order_by(AuditReport.created_at.desc()).offset(skip).limit(limit).all()

    def get(self, report_id: int) -> AuditReport:
        report = self.db.query(AuditReport).filter(AuditReport.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
