from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Observation, User
from app.schemas import AuditReportCreate, AuditReportOut
from app.services.reports import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def _observation_count(db: Session, report_id: int) -> int:
    return db.query(func.count(Observation.id)).filter(Observation.report_id == report_id).scalar() or 0


@router.get("", response_model=list[AuditReportOut])
def list_reports(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 50,
):
    service = ReportService(db)
    reports = service.list(skip=skip, limit=limit)
    result = []
    for r in reports:
        out = AuditReportOut.model_validate(r)
        out.observation_count = _observation_count(db, r.id)
        result.append(out)
    return result


@router.post("", response_model=AuditReportOut, status_code=201)
async def create_report(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    title: str = Form(...),
    report_number: str = Form(...),
    description: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    service = ReportService(db)
    data = AuditReportCreate(title=title, report_number=report_number, description=description)
    report = service.create(data, user, file)
    out = AuditReportOut.model_validate(report)
    out.observation_count = 0
    return out


@router.get("/{report_id}", response_model=AuditReportOut)
def get_report(
    report_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    report = ReportService(db).get(report_id)
    out = AuditReportOut.model_validate(report)
    out.observation_count = _observation_count(db, report.id)
    return out
