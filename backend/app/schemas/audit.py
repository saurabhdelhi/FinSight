"""Audit schemas — run requests, findings, summaries."""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class AuditRunRequest(BaseModel):
    rule_ids: list[str] | None = None  # None = run all rules


class AuditFindingResponse(BaseModel):
    id: str
    rule_id: str
    severity: str
    category: str
    title: str
    description: str
    ledger_name: str | None
    amount: Decimal | None
    recommendation: str | None
    reference: str | None

    model_config = {"from_attributes": True}


class AuditRunResponse(BaseModel):
    id: str
    run_at: datetime
    status: str
    rules_executed: int
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    risk_score: float
    duration_seconds: float | None
    findings: list[AuditFindingResponse]

    model_config = {"from_attributes": True}


class AuditSummaryResponse(BaseModel):
    client_id: str
    latest_run: AuditRunResponse | None
    total_runs: int
    findings_trend: list[dict]  # [{run_id, date, total_findings, risk_score}]


class RuleInfoResponse(BaseModel):
    rule_id: str
    title: str
    category: str
    severity: str
    description: str
