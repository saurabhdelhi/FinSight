"""Audit API — run audit, view findings, list rules."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import CurrentUser, DBSession
from app.models.audit import AuditRun
from app.models.client import TallyClient
from app.schemas.audit import (
    AuditFindingResponse,
    AuditRunRequest,
    AuditRunResponse,
    AuditSummaryResponse,
    RuleInfoResponse,
)
from app.services.audit_engine import AuditEngine

router = APIRouter(prefix="/api/clients/{client_id}/audit", tags=["Audit"])


async def _verify_client(client_id: str, user: CurrentUser, db: DBSession):
    result = await db.execute(
        select(TallyClient).where(
            TallyClient.id == client_id,
            TallyClient.org_id == user.org_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")


@router.post("/run", response_model=AuditRunResponse)
async def run_audit(
    client_id: str,
    payload: AuditRunRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Execute audit rules against the client's synced data."""
    await _verify_client(client_id, current_user, db)
    engine = AuditEngine(db)
    audit_run = await engine.run_audit(client_id, rule_ids=payload.rule_ids)

    # Reload with findings
    result = await db.execute(
        select(AuditRun)
        .where(AuditRun.id == audit_run.id)
        .options(selectinload(AuditRun.findings))
    )
    audit_run = result.scalar_one()

    return AuditRunResponse(
        id=audit_run.id,
        run_at=audit_run.run_at,
        status=audit_run.status,
        rules_executed=audit_run.rules_executed,
        total_findings=audit_run.total_findings,
        critical_count=audit_run.critical_count,
        high_count=audit_run.high_count,
        medium_count=audit_run.medium_count,
        low_count=audit_run.low_count,
        info_count=audit_run.info_count,
        risk_score=audit_run.risk_score,
        duration_seconds=audit_run.duration_seconds,
        findings=[
            AuditFindingResponse.model_validate(f) for f in audit_run.findings
        ],
    )


@router.get("/latest", response_model=AuditRunResponse | None)
async def get_latest_audit(
    client_id: str, current_user: CurrentUser, db: DBSession
):
    """Get the most recent audit run and its findings."""
    await _verify_client(client_id, current_user, db)
    engine = AuditEngine(db)
    audit_run = await engine.get_latest_audit(client_id)

    if not audit_run:
        return None

    return AuditRunResponse(
        id=audit_run.id,
        run_at=audit_run.run_at,
        status=audit_run.status,
        rules_executed=audit_run.rules_executed,
        total_findings=audit_run.total_findings,
        critical_count=audit_run.critical_count,
        high_count=audit_run.high_count,
        medium_count=audit_run.medium_count,
        low_count=audit_run.low_count,
        info_count=audit_run.info_count,
        risk_score=audit_run.risk_score,
        duration_seconds=audit_run.duration_seconds,
        findings=[
            AuditFindingResponse.model_validate(f) for f in audit_run.findings
        ],
    )


@router.get("/findings", response_model=list[AuditFindingResponse])
async def get_findings(
    client_id: str,
    current_user: CurrentUser,
    db: DBSession,
    severity: str | None = None,
    category: str | None = None,
):
    """Get all findings from the latest audit, with optional filters."""
    await _verify_client(client_id, current_user, db)
    engine = AuditEngine(db)
    audit_run = await engine.get_latest_audit(client_id)

    if not audit_run:
        return []

    findings = audit_run.findings
    if severity:
        findings = [f for f in findings if f.severity.value == severity]
    if category:
        findings = [f for f in findings if f.category == category]

    return [AuditFindingResponse.model_validate(f) for f in findings]


@router.get("/rules", response_model=list[RuleInfoResponse])
async def list_rules(
    client_id: str, current_user: CurrentUser, db: DBSession
):
    """List all available audit rules."""
    await _verify_client(client_id, current_user, db)
    engine = AuditEngine(db)
    rules = await engine.get_available_rules()
    return [RuleInfoResponse(**r) for r in rules]
