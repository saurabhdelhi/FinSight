"""
Audit engine — orchestrates the execution of audit rules.

Loads synced data into an AuditContext, runs all (or selected) rules,
aggregates findings, computes a risk score, and persists results.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NoSyncDataError
from app.models.audit import AuditFinding as AuditFindingModel
from app.models.audit import AuditRun
from app.models.audit import Severity as SeverityEnum
from app.models.client import TallyClient
from app.models.tally import TallyGroup, TallyLedger, TallyVoucher
from app.services.audit_rules.base import (
    AuditContext,
    AuditRule,
    Finding,
    Severity,
    get_all_rules,
    get_rule_by_id,
)

logger = logging.getLogger(__name__)

# ── Risk score weights by severity ───────────────────────────────────────
SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 10.0,
    Severity.HIGH: 5.0,
    Severity.MEDIUM: 2.0,
    Severity.LOW: 0.5,
    Severity.INFO: 0.1,
}
MAX_RISK_SCORE = 100.0


def _compute_risk_score(findings: list[Finding]) -> float:
    """
    Compute a 0-100 risk score based on severity-weighted findings.
    Uses a logarithmic scale so the score doesn't linearly explode
    with more findings.
    """
    import math

    raw = sum(SEVERITY_WEIGHTS.get(f.severity, 1.0) for f in findings)
    # Logarithmic normalization: score approaches 100 as raw grows
    if raw == 0:
        return 0.0
    score = min(MAX_RISK_SCORE, (math.log(1 + raw) / math.log(1 + 200)) * 100)
    return round(score, 1)


class AuditEngine:
    """
    Executes audit rules against a client's synced Tally data.

    Usage:
        engine = AuditEngine(db_session)
        audit_run = await engine.run_audit(client_id)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _build_context(self, client_id: str) -> AuditContext:
        """Load all synced data for a client into an AuditContext."""
        # Get client
        result = await self.db.execute(
            select(TallyClient).where(TallyClient.id == client_id)
        )
        client = result.scalar_one_or_none()
        if not client:
            from app.core.exceptions import ClientNotFoundError
            raise ClientNotFoundError(client_id)

        # Check if data exists
        ledger_count = await self.db.scalar(
            select(func.count()).select_from(TallyLedger).where(
                TallyLedger.client_id == client_id
            )
        )
        if not ledger_count:
            raise NoSyncDataError(client_id)

        # Load ledgers
        result = await self.db.execute(
            select(TallyLedger).where(TallyLedger.client_id == client_id)
        )
        ledgers = list(result.scalars().all())

        # Load groups
        result = await self.db.execute(
            select(TallyGroup).where(TallyGroup.client_id == client_id)
        )
        groups = list(result.scalars().all())

        # Load vouchers with entries
        result = await self.db.execute(
            select(TallyVoucher)
            .where(TallyVoucher.client_id == client_id)
            .options(selectinload(TallyVoucher.entries))
        )
        vouchers = list(result.scalars().all())

        # Build context with indexes
        ctx = AuditContext(
            client_id=client_id,
            financial_year=client.financial_year,
            ledgers=ledgers,
            groups=groups,
            vouchers=vouchers,
        )
        ctx.build_indexes()

        logger.info(
            f"Audit context built: {len(ledgers)} ledgers, "
            f"{len(groups)} groups, {len(vouchers)} vouchers"
        )
        return ctx

    async def run_audit(
        self,
        client_id: str,
        rule_ids: list[str] | None = None,
    ) -> AuditRun:
        """
        Run audit rules and persist results.

        Args:
            client_id: The Tally client to audit
            rule_ids: Optional list of specific rule IDs to run.
                      None = run all rules.
        """
        start_time = time.monotonic()

        # Build context
        ctx = await self._build_context(client_id)

        # Get rules to execute
        if rule_ids:
            rules = [r for r in get_all_rules() if r.rule_id in rule_ids]
        else:
            rules = get_all_rules()

        logger.info(f"Running {len(rules)} audit rules for client {client_id[:8]}")

        # Execute rules concurrently
        all_findings: list[Finding] = []
        tasks = [rule.evaluate(ctx) for rule in rules]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for rule, result in zip(rules, results):
            if isinstance(result, Exception):
                logger.error(f"Rule {rule.rule_id} failed: {result}")
                all_findings.append(Finding(
                    rule_id=rule.rule_id,
                    severity=Severity.INFO,
                    category=rule.category,
                    title=f"Rule {rule.rule_id} execution failed",
                    description=f"Error: {str(result)}",
                    recommendation="Check the rule implementation and data quality.",
                ))
            else:
                all_findings.extend(result)

        # Compute risk score
        risk_score = _compute_risk_score(all_findings)

        # Count by severity
        severity_counts = {s: 0 for s in Severity}
        for f in all_findings:
            severity_counts[f.severity] += 1

        duration = time.monotonic() - start_time

        # Create audit run record
        audit_run = AuditRun(
            client_id=client_id,
            run_at=datetime.now(timezone.utc),
            status="completed",
            rules_executed=len(rules),
            total_findings=len(all_findings),
            critical_count=severity_counts[Severity.CRITICAL],
            high_count=severity_counts[Severity.HIGH],
            medium_count=severity_counts[Severity.MEDIUM],
            low_count=severity_counts[Severity.LOW],
            info_count=severity_counts[Severity.INFO],
            risk_score=risk_score,
            duration_seconds=round(duration, 2),
        )
        self.db.add(audit_run)
        await self.db.flush()

        # Create finding records
        for f in all_findings:
            finding_model = AuditFindingModel(
                audit_run_id=audit_run.id,
                rule_id=f.rule_id,
                severity=SeverityEnum(f.severity.value),
                category=f.category,
                title=f.title,
                description=f.description,
                ledger_name=f.ledger_name,
                amount=f.amount,
                recommendation=f.recommendation,
                reference=f.reference,
                details_json=json.dumps(f.details) if f.details else None,
            )
            self.db.add(finding_model)

        await self.db.flush()

        logger.info(
            f"Audit completed: {len(all_findings)} findings, "
            f"risk score {risk_score}, took {duration:.2f}s"
        )
        return audit_run

    async def get_latest_audit(self, client_id: str) -> AuditRun | None:
        """Get the most recent audit run for a client."""
        result = await self.db.execute(
            select(AuditRun)
            .where(AuditRun.client_id == client_id)
            .options(selectinload(AuditRun.findings))
            .order_by(AuditRun.run_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_available_rules(self) -> list[dict]:
        """List all available audit rules with metadata."""
        rules = get_all_rules()
        return [
            {
                "rule_id": r.rule_id,
                "title": r.title,
                "category": r.category,
                "severity": r.default_severity.value,
                "description": r.description,
            }
            for r in sorted(rules, key=lambda r: r.rule_id)
        ]
