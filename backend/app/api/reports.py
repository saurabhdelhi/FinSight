"""Report generation & download API."""

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DBSession
from app.models.client import TallyClient
from app.models.report import GeneratedReport
from app.schemas.report import ReportGenerateRequest, ReportListResponse, ReportResponse
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/api", tags=["Reports"])


async def _verify_client(client_id: str, user: CurrentUser, db: DBSession):
    result = await db.execute(
        select(TallyClient).where(
            TallyClient.id == client_id,
            TallyClient.org_id == user.org_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")


@router.post("/clients/{client_id}/reports/generate", response_model=ReportResponse)
async def generate_report(
    client_id: str,
    payload: ReportGenerateRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Generate a new report (Excel or PDF)."""
    await _verify_client(client_id, current_user, db)
    generator = ReportGenerator(db)
    report = await generator.generate_report(
        client_id=client_id,
        report_type=payload.report_type,
        report_format=payload.report_format,
    )
    return ReportResponse.model_validate(report)


@router.get("/clients/{client_id}/reports", response_model=ReportListResponse)
async def list_reports(client_id: str, current_user: CurrentUser, db: DBSession):
    """List all generated reports for a client."""
    await _verify_client(client_id, current_user, db)
    generator = ReportGenerator(db)
    reports = await generator.get_reports(client_id)
    return ReportListResponse(
        reports=[ReportResponse.model_validate(r) for r in reports],
        total=len(reports),
    )


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str, current_user: CurrentUser, db: DBSession):
    """Download a generated report file."""
    result = await db.execute(
        select(GeneratedReport).where(GeneratedReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Verify the report belongs to the user's org
    result = await db.execute(
        select(TallyClient).where(
            TallyClient.id == report.client_id,
            TallyClient.org_id == current_user.org_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if report.report_format.value == "xlsx"
        else "application/pdf"
    )

    return FileResponse(
        path=report.file_path,
        filename=report.file_name,
        media_type=media_type,
    )
