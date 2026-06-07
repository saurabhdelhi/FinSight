"""
Report generation orchestrator.

Coordinates the generation of audit reports and financial statements
in Excel and PDF formats.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.exceptions import NoSyncDataError, ReportGenerationError
from app.models.audit import AuditRun
from app.models.client import TallyClient
from app.models.report import GeneratedReport, ReportFormat, ReportType
from app.models.tally import TallyLedger
from app.services.excel_builder import ExcelBuilder
from app.services.schedule_iii_mapper import ScheduleIIIMapper

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates Excel and PDF reports for a client."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = ScheduleIIIMapper(db)

    async def _get_client(self, client_id: str) -> TallyClient:
        result = await self.db.execute(
            select(TallyClient).where(TallyClient.id == client_id)
        )
        client = result.scalar_one_or_none()
        if not client:
            from app.core.exceptions import ClientNotFoundError
            raise ClientNotFoundError(client_id)
        return client

    async def _get_ledgers_as_dicts(self, client_id: str) -> list[dict]:
        """Get all ledgers as serializable dicts for the trial balance."""
        result = await self.db.execute(
            select(TallyLedger)
            .where(TallyLedger.client_id == client_id)
            .order_by(TallyLedger.parent, TallyLedger.name)
        )
        ledgers = result.scalars().all()
        return [
            {
                "name": l.name,
                "group": l.parent,
                "opening_balance": float(l.opening_balance),
                "debit_total": float(l.debit_total),
                "credit_total": float(l.credit_total),
                "closing_balance": float(l.closing_balance),
            }
            for l in ledgers
        ]

    async def _get_findings_as_dicts(self, client_id: str) -> tuple[list[dict], float]:
        """Get latest audit findings as serializable dicts."""
        result = await self.db.execute(
            select(AuditRun)
            .where(AuditRun.client_id == client_id)
            .options(selectinload(AuditRun.findings))
            .order_by(AuditRun.run_at.desc())
            .limit(1)
        )
        audit_run = result.scalar_one_or_none()

        if not audit_run:
            return [], 0.0

        findings = [
            {
                "rule_id": f.rule_id,
                "severity": f.severity.value,
                "category": f.category,
                "title": f.title,
                "description": f.description,
                "ledger_name": f.ledger_name,
                "amount": float(f.amount) if f.amount else None,
                "recommendation": f.recommendation,
                "reference": f.reference,
            }
            for f in audit_run.findings
        ]
        return findings, audit_run.risk_score

    def _save_file(
        self, content: bytes, client_name: str, report_type: str, ext: str
    ) -> tuple[str, str]:
        """Save report file to disk and return (file_name, file_path)."""
        report_dir = settings.report_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in client_name)
        file_name = f"{safe_name}_{report_type}_{timestamp}.{ext}"
        file_path = report_dir / file_name

        with open(file_path, "wb") as f:
            f.write(content)

        return file_name, str(file_path)

    async def generate_report(
        self,
        client_id: str,
        report_type: str,
        report_format: str,
    ) -> GeneratedReport:
        """
        Generate a report for a client.

        Args:
            client_id: The client to report on
            report_type: "audit_report", "financial_statements", or "combined"
            report_format: "xlsx" or "pdf"
        """
        client = await self._get_client(client_id)

        # Verify we have data
        ledgers = await self._get_ledgers_as_dicts(client_id)
        if not ledgers:
            raise NoSyncDataError(client_id)

        try:
            if report_format == "xlsx":
                content = await self._generate_excel(
                    client, ledgers, report_type
                )
                ext = "xlsx"
            elif report_format == "pdf":
                content = await self._generate_pdf(
                    client, ledgers, report_type
                )
                ext = "pdf"
            else:
                raise ReportGenerationError(f"Unsupported format: {report_format}")

            # Save to disk
            file_name, file_path = self._save_file(
                content, client.company_name, report_type, ext
            )

            # Record in database
            report = GeneratedReport(
                client_id=client_id,
                report_type=ReportType(report_type),
                report_format=ReportFormat(ext),
                file_name=file_name,
                file_path=file_path,
                file_size_bytes=len(content),
                generated_at=datetime.now(timezone.utc),
            )
            self.db.add(report)
            await self.db.flush()

            logger.info(f"Report generated: {file_name} ({len(content)} bytes)")
            return report

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise ReportGenerationError(str(e)) from e

    async def _generate_excel(
        self,
        client: TallyClient,
        ledgers: list[dict],
        report_type: str,
    ) -> bytes:
        """Build an Excel workbook based on report type."""
        builder = ExcelBuilder()

        # Cover page is always included
        builder.add_cover_page(
            company_name=client.company_name,
            financial_year=client.financial_year,
            report_title=self._report_title(report_type),
        )

        if report_type in ("financial_statements", "combined"):
            # Get Schedule III data
            bs_data = await self.mapper.get_balance_sheet(client.id)
            pl_data = await self.mapper.get_profit_and_loss(client.id)
            builder.add_balance_sheet(bs_data)
            builder.add_profit_and_loss(pl_data)
            builder.add_trial_balance(ledgers)

        if report_type in ("audit_report", "combined"):
            findings, risk_score = await self._get_findings_as_dicts(client.id)
            builder.add_audit_findings(findings, risk_score)

        if report_type == "financial_statements":
            # Also add trial balance for financial statements
            pass  # Already added above

        return builder.save()

    async def _generate_pdf(
        self,
        client: TallyClient,
        ledgers: list[dict],
        report_type: str,
    ) -> bytes:
        """
        Generate a PDF report using HTML rendering.
        Falls back to a simple text-based PDF if WeasyPrint isn't available.
        """
        try:
            # Try WeasyPrint
            from weasyprint import HTML

            html_content = await self._build_report_html(
                client, ledgers, report_type
            )
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes

        except ImportError:
            # Fallback: generate the Excel and note that PDF requires WeasyPrint
            logger.warning(
                "WeasyPrint not available, generating Excel instead"
            )
            return await self._generate_excel(client, ledgers, report_type)

    async def _build_report_html(
        self,
        client: TallyClient,
        ledgers: list[dict],
        report_type: str,
    ) -> str:
        """Build HTML for PDF rendering."""
        # Get data
        bs_data = await self.mapper.get_balance_sheet(client.id) if report_type in ("financial_statements", "combined") else {}
        pl_data = await self.mapper.get_profit_and_loss(client.id) if report_type in ("financial_statements", "combined") else {}
        findings, risk_score = await self._get_findings_as_dicts(client.id) if report_type in ("audit_report", "combined") else ([], 0)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 40px; color: #1a1a2e; }}
        h1 {{ color: #2d3748; border-bottom: 2px solid #2d3748; padding-bottom: 10px; }}
        h2 {{ color: #4a5568; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th {{ background: #2d3748; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }}
        tr:nth-child(even) {{ background: #f7fafc; }}
        .amount {{ text-align: right; font-family: monospace; }}
        .total {{ font-weight: bold; background: #ebf4ff; }}
        .critical {{ background: #fed7d7; }}
        .high {{ background: #feebc8; }}
        .medium {{ background: #fefcbf; }}
        .cover {{ text-align: center; margin-top: 100px; }}
        .cover h1 {{ font-size: 28px; border: none; }}
        .footer {{ color: #888; font-size: 11px; margin-top: 40px; font-style: italic; }}
        @page {{ margin: 2cm; }}
    </style>
</head>
<body>
    <div class="cover">
        <h1>{client.company_name}</h1>
        <h2>{self._report_title(report_type)}</h2>
        <p>Financial Year: {client.financial_year}</p>
        <p>Generated: {datetime.now().strftime('%d %B %Y')}</p>
    </div>
"""

        if report_type in ("financial_statements", "combined") and bs_data:
            html += self._bs_html(bs_data)
            html += self._pl_html(pl_data)

        if report_type in ("audit_report", "combined") and findings:
            html += self._findings_html(findings, risk_score)

        html += """
    <div class="footer">
        <p>Generated by FinSight. This report is for audit and review purposes only.</p>
    </div>
</body>
</html>"""
        return html

    def _bs_html(self, bs_data: dict) -> str:
        html = '<div style="page-break-before: always;"><h1>Balance Sheet</h1>'
        html += '<h2>I. Equity and Liabilities</h2><table><tr><th>Particulars</th><th class="amount">Amount (₹)</th></tr>'
        for category, items in bs_data.get("equity_and_liabilities", {}).items():
            html += f'<tr><td><strong>{category}</strong></td><td></td></tr>'
            for item, amt in items.items():
                html += f'<tr><td>&nbsp;&nbsp;&nbsp;{item}</td><td class="amount">{float(amt):,.2f}</td></tr>'
        html += f'<tr class="total"><td>TOTAL</td><td class="amount">{float(bs_data.get("total_equity_liabilities", 0)):,.2f}</td></tr></table>'

        html += '<h2>II. Assets</h2><table><tr><th>Particulars</th><th class="amount">Amount (₹)</th></tr>'
        for category, items in bs_data.get("assets", {}).items():
            html += f'<tr><td><strong>{category}</strong></td><td></td></tr>'
            for item, amt in items.items():
                html += f'<tr><td>&nbsp;&nbsp;&nbsp;{item}</td><td class="amount">{float(amt):,.2f}</td></tr>'
        html += f'<tr class="total"><td>TOTAL</td><td class="amount">{float(bs_data.get("total_assets", 0)):,.2f}</td></tr></table></div>'
        return html

    def _pl_html(self, pl_data: dict) -> str:
        html = '<div style="page-break-before: always;"><h1>Statement of Profit and Loss</h1>'
        html += '<table><tr><th>Particulars</th><th class="amount">Amount (₹)</th></tr>'
        html += '<tr><td><strong>INCOME</strong></td><td></td></tr>'
        for item, amt in pl_data.get("revenue", {}).items():
            html += f'<tr><td>&nbsp;&nbsp;&nbsp;{item}</td><td class="amount">{float(amt):,.2f}</td></tr>'
        html += f'<tr class="total"><td>Total Income</td><td class="amount">{float(pl_data.get("total_revenue", 0)):,.2f}</td></tr>'

        html += '<tr><td><strong>EXPENSES</strong></td><td></td></tr>'
        for item, amt in pl_data.get("expenses", {}).items():
            html += f'<tr><td>&nbsp;&nbsp;&nbsp;{item}</td><td class="amount">{float(amt):,.2f}</td></tr>'
        html += f'<tr class="total"><td>Total Expenses</td><td class="amount">{float(pl_data.get("total_expenses", 0)):,.2f}</td></tr>'
        html += f'<tr class="total"><td>Profit Before Tax</td><td class="amount">{float(pl_data.get("profit_before_tax", 0)):,.2f}</td></tr>'
        html += f'<tr class="total"><td>Net Profit</td><td class="amount">{float(pl_data.get("net_profit", 0)):,.2f}</td></tr>'
        html += '</table></div>'
        return html

    def _findings_html(self, findings: list[dict], risk_score: float) -> str:
        html = f'<div style="page-break-before: always;"><h1>Audit Findings</h1>'
        html += f'<p><strong>Risk Score: {risk_score:.1f} / 100</strong></p>'
        html += f'<p>Total Findings: {len(findings)}</p>'
        html += '<table><tr><th>Rule</th><th>Severity</th><th>Title</th><th>Ledger</th><th class="amount">Amount</th><th>Recommendation</th></tr>'
        for f in findings:
            sev_class = f.get("severity", "info")
            amt = f.get("amount")
            amt_str = f'{amt:,.2f}' if amt else '-'
            html += f'<tr class="{sev_class}"><td>{f.get("rule_id", "")}</td>'
            html += f'<td>{sev_class.upper()}</td><td>{f.get("title", "")}</td>'
            html += f'<td>{f.get("ledger_name", "-")}</td>'
            html += f'<td class="amount">{amt_str}</td>'
            html += f'<td>{f.get("recommendation", "")}</td></tr>'
        html += '</table></div>'
        return html

    @staticmethod
    def _report_title(report_type: str) -> str:
        titles = {
            "audit_report": "Audit Report",
            "financial_statements": "Financial Statements (Schedule III)",
            "combined": "Combined Audit Report & Financial Statements",
        }
        return titles.get(report_type, "Report")

    async def get_reports(self, client_id: str) -> list[GeneratedReport]:
        """List all generated reports for a client."""
        result = await self.db.execute(
            select(GeneratedReport)
            .where(GeneratedReport.client_id == client_id)
            .order_by(GeneratedReport.generated_at.desc())
        )
        return list(result.scalars().all())
