"""
Statutory compliance audit rules.

Rules focused on TDS, GST, PF/ESI, Professional Tax, and other
statutory dues compliance under Indian tax law.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.audit_rules.base import AuditContext, AuditRule, Finding, Severity


class TDSLiabilityOutstanding(AuditRule):
    """STAT_001: TDS liability outstanding beyond due date."""

    rule_id = "STAT_001"
    title = "TDS Liability Outstanding"
    category = "Statutory Compliance"
    default_severity = Severity.HIGH
    description = (
        "Checks if TDS payable ledgers have outstanding balances, indicating "
        "TDS has been deducted but not deposited with the government."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        tds_keywords = ("tds", "tax deducted", "t.d.s")
        duties_ledgers = ctx.get_ledgers_in_group_recursive("Duties & Taxes")

        for ledger in duties_ledgers:
            name_lower = ledger.name.lower()
            if any(kw in name_lower for kw in tds_keywords):
                # Credit balance in TDS = outstanding liability
                if ledger.closing_balance > Decimal("0"):
                    findings.append(self.finding(
                        title=f"TDS payable outstanding: ₹{ledger.closing_balance:,.2f}",
                        description=(
                            f"Ledger '{ledger.name}' shows an outstanding TDS "
                            f"liability of ₹{ledger.closing_balance:,.2f}. "
                            f"TDS must be deposited by the 7th of the following month "
                            f"(30th April for March). Late deposit attracts interest "
                            f"under Section 201(1A) at 1.5% per month."
                        ),
                        ledger_name=ledger.name,
                        amount=ledger.closing_balance,
                        recommendation=(
                            "Verify TDS deposit challan dates against deduction dates. "
                            "Deposit outstanding TDS immediately. Calculate interest "
                            "liability u/s 201(1A) for any delays."
                        ),
                        reference="Section 200(1)/201(1A), Income Tax Act 1961",
                    ))
        return findings


class GSTInputCreditAnomaly(AuditRule):
    """STAT_002: GST input credit anomalies."""

    rule_id = "STAT_002"
    title = "GST Input Credit Anomaly"
    category = "Statutory Compliance"
    default_severity = Severity.MEDIUM
    description = (
        "Checks for anomalies in GST input credit ledgers — outstanding "
        "balances that may indicate unmatched credits or filing gaps."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        gst_keywords = ("gst", "cgst", "sgst", "igst", "input", "output")
        duties_ledgers = ctx.get_ledgers_in_group_recursive("Duties & Taxes")

        input_total = Decimal("0")
        output_total = Decimal("0")

        for ledger in duties_ledgers:
            name_lower = ledger.name.lower()
            if "input" in name_lower and any(
                kw in name_lower for kw in ("gst", "cgst", "sgst", "igst")
            ):
                input_total += abs(ledger.closing_balance)
            elif "output" in name_lower and any(
                kw in name_lower for kw in ("gst", "cgst", "sgst", "igst")
            ):
                output_total += abs(ledger.closing_balance)

        # Large input credit balance at year-end
        if input_total > Decimal("100000"):
            findings.append(self.finding(
                title=f"GST input credit balance: ₹{input_total:,.2f}",
                description=(
                    f"Total GST input tax credit outstanding at year-end is "
                    f"₹{input_total:,.2f}. Verify that all input credits are "
                    f"matched with valid invoices in GSTR-2B and that ITC is "
                    f"eligible under Section 16 of CGST Act."
                ),
                amount=input_total,
                recommendation=(
                    "Reconcile ITC with GSTR-2B. Reverse any ineligible ITC "
                    "under Section 17(5). Ensure all credits are claimed within "
                    "the time limit prescribed under Section 16(4)."
                ),
                reference="Section 16, CGST Act 2017",
            ))
        return findings


class PFESIDelayed(AuditRule):
    """STAT_003: PF/ESI deposits delayed beyond due date."""

    rule_id = "STAT_003"
    title = "PF/ESI Deposit Delay"
    category = "Statutory Compliance"
    default_severity = Severity.HIGH
    description = (
        "Checks if Provident Fund and ESI payable ledgers have outstanding "
        "balances, indicating delayed deposits. PF/ESI must be deposited by "
        "the 15th of the following month."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        pf_esi_keywords = (
            "provident fund", "pf payable", "p.f.", "epf",
            "esi payable", "e.s.i.", "esic",
        )
        duties_ledgers = ctx.get_ledgers_in_group_recursive("Duties & Taxes")
        provision_ledgers = ctx.get_ledgers_in_group_recursive("Provisions")
        all_relevant = duties_ledgers + provision_ledgers

        for ledger in all_relevant:
            name_lower = ledger.name.lower()
            if any(kw in name_lower for kw in pf_esi_keywords):
                if abs(ledger.closing_balance) > Decimal("0"):
                    findings.append(self.finding(
                        title=(
                            f"{'PF' if 'pf' in name_lower or 'provident' in name_lower else 'ESI'} "
                            f"payable outstanding: ₹{abs(ledger.closing_balance):,.2f}"
                        ),
                        description=(
                            f"Ledger '{ledger.name}' shows an outstanding balance of "
                            f"₹{abs(ledger.closing_balance):,.2f}. Employee PF/ESI "
                            f"contributions must be deposited by the 15th of the "
                            f"following month. Delayed deposit disallows the expense "
                            f"under Section 36(1)(va) and 43B."
                        ),
                        ledger_name=ledger.name,
                        amount=abs(ledger.closing_balance),
                        recommendation=(
                            "Verify deposit dates. If deposited after the due date, "
                            "the employer's contribution is disallowed under Section 43B "
                            "and employee's contribution under Section 36(1)(va). "
                            "Also check CARO 2020 reporting requirements."
                        ),
                        reference="Section 36(1)(va) / 43B, Income Tax Act 1961",
                    ))
        return findings


class ProfessionalTaxOutstanding(AuditRule):
    """STAT_004: Professional tax not deposited."""

    rule_id = "STAT_004"
    title = "Professional Tax Outstanding"
    category = "Statutory Compliance"
    default_severity = Severity.MEDIUM
    description = (
        "Checks if professional tax payable has an outstanding balance "
        "at year-end."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        pt_keywords = ("professional tax", "prof tax", "prof. tax", "p.tax")
        duties_ledgers = ctx.get_ledgers_in_group_recursive("Duties & Taxes")

        for ledger in duties_ledgers:
            name_lower = ledger.name.lower()
            if any(kw in name_lower for kw in pt_keywords):
                if abs(ledger.closing_balance) > Decimal("500"):
                    findings.append(self.finding(
                        title=f"Professional tax outstanding: ₹{abs(ledger.closing_balance):,.2f}",
                        description=(
                            f"Ledger '{ledger.name}' has an outstanding balance of "
                            f"₹{abs(ledger.closing_balance):,.2f}. Professional tax "
                            f"must be deposited as per state-specific due dates."
                        ),
                        ledger_name=ledger.name,
                        amount=abs(ledger.closing_balance),
                        recommendation=(
                            "Deposit professional tax as per the applicable state "
                            "schedule. Delayed payment may attract interest and "
                            "penalty under the respective state PT Act."
                        ),
                        reference="Respective State Professional Tax Act",
                    ))
        return findings


class StatutoryDuesOutstanding(AuditRule):
    """STAT_005: Any statutory dues outstanding at year-end."""

    rule_id = "STAT_005"
    title = "Statutory Dues Outstanding at Year-End"
    category = "Statutory Compliance"
    default_severity = Severity.MEDIUM
    description = (
        "Provides a summary of all outstanding statutory dues at year-end "
        "for CARO 2020 reporting (Clause vii)."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        duties_ledgers = ctx.get_ledgers_in_group_recursive("Duties & Taxes")

        outstanding = []
        for ledger in duties_ledgers:
            if abs(ledger.closing_balance) > Decimal("100"):
                outstanding.append({
                    "name": ledger.name,
                    "amount": float(abs(ledger.closing_balance)),
                })

        if outstanding:
            total = sum(item["amount"] for item in outstanding)
            findings.append(self.finding(
                title=f"{len(outstanding)} statutory dues outstanding totalling ₹{total:,.2f}",
                description=(
                    f"There are {len(outstanding)} statutory dues with outstanding "
                    f"balances at year-end, totalling ₹{total:,.2f}. These need "
                    f"to be reported under CARO 2020 Clause (vii). "
                    f"Dues: {', '.join(d['name'] for d in outstanding[:5])}"
                    f"{'...' if len(outstanding) > 5 else ''}"
                ),
                severity=Severity.INFO,
                amount=Decimal(str(total)),
                recommendation=(
                    "Prepare a schedule of statutory dues for CARO reporting. "
                    "Verify deposit dates for each outstanding amount. "
                    "Classify as 'not yet due' or 'overdue' as applicable."
                ),
                reference="CARO 2020, Clause (vii)",
            ))
        return findings


class AdvanceTaxNotPaid(AuditRule):
    """STAT_006: Advance tax instalments not paid per schedule."""

    rule_id = "STAT_006"
    title = "Advance Tax Payment Check"
    category = "Statutory Compliance"
    default_severity = Severity.MEDIUM
    description = (
        "Checks if advance tax / income tax ledgers indicate potential "
        "non-compliance with advance tax instalment schedule."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        tax_keywords = ("income tax", "advance tax", "self assessment tax", "i.t.")
        duties_ledgers = ctx.get_ledgers_in_group_recursive("Duties & Taxes")

        for ledger in duties_ledgers:
            name_lower = ledger.name.lower()
            if any(kw in name_lower for kw in tax_keywords):
                if abs(ledger.closing_balance) > Decimal("10000"):
                    findings.append(self.finding(
                        title=f"Tax provision outstanding: ₹{abs(ledger.closing_balance):,.2f}",
                        description=(
                            f"Ledger '{ledger.name}' has a balance of "
                            f"₹{abs(ledger.closing_balance):,.2f}. Verify that "
                            f"advance tax has been paid per the quarterly schedule "
                            f"(15% by Jun 15, 45% by Sep 15, 75% by Dec 15, "
                            f"100% by Mar 15). Interest u/s 234B/234C applies "
                            f"for shortfall."
                        ),
                        ledger_name=ledger.name,
                        amount=abs(ledger.closing_balance),
                        recommendation=(
                            "Reconcile advance tax payments with Form 26AS. "
                            "Calculate interest liability under Sections 234B "
                            "and 234C for any instalment shortfalls."
                        ),
                        reference="Section 208/234B/234C, Income Tax Act 1961",
                    ))
        return findings
