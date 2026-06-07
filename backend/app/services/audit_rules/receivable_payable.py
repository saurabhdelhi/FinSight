"""
Receivables & Payables audit rules.

Rules focused on trade debtors, creditors, aging analysis,
and provision adequacy.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.audit_rules.base import AuditContext, AuditRule, Finding, Severity


class DebtorsOverdue(AuditRule):
    """AP_001: Sundry debtors outstanding potentially over 180 days."""

    rule_id = "AP_001"
    title = "Potential Overdue Debtors"
    category = "Receivables & Payables"
    default_severity = Severity.HIGH
    description = (
        "Identifies sundry debtor ledgers with balances that may be overdue. "
        "Debtors outstanding for more than 180 days are considered doubtful."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        debtor_ledgers = ctx.get_ledgers_in_group_recursive("Sundry Debtors")

        if not debtor_ledgers:
            return findings

        total_debtors = sum(abs(l.closing_balance) for l in debtor_ledgers)
        large_threshold = total_debtors * Decimal("0.1") if total_debtors > 0 else Decimal("100000")

        for ledger in debtor_ledgers:
            balance = abs(ledger.closing_balance)
            # Flag large individual debtors (>10% of total or > ₹5L)
            if balance > max(large_threshold, Decimal("500000")):
                # Check if balance = opening (no movement = likely overdue)
                if ledger.opening_balance == ledger.closing_balance:
                    findings.append(self.finding(
                        title=(
                            f"Potentially overdue debtor: '{ledger.name}' "
                            f"₹{balance:,.2f}"
                        ),
                        severity=Severity.HIGH,
                        description=(
                            f"Debtor '{ledger.name}' has an outstanding balance of "
                            f"₹{balance:,.2f} with no movement during the year, "
                            f"suggesting the balance is overdue beyond 365 days. "
                            f"This may require a provision for doubtful debts."
                        ),
                        ledger_name=ledger.name,
                        amount=balance,
                        recommendation=(
                            "Obtain debtor confirmation (SA 505). Review aging "
                            "analysis. Consider making a provision for doubtful "
                            "debts. Report as doubtful if >6 months old."
                        ),
                        reference="SA 505 / AS-4 / AS-29",
                    ))
                elif balance > Decimal("500000"):
                    findings.append(self.finding(
                        title=(
                            f"Large debtor balance: '{ledger.name}' "
                            f"₹{balance:,.2f}"
                        ),
                        severity=Severity.MEDIUM,
                        description=(
                            f"Debtor '{ledger.name}' has a large outstanding "
                            f"balance of ₹{balance:,.2f}. Verify collectability "
                            f"and review aging of this receivable."
                        ),
                        ledger_name=ledger.name,
                        amount=balance,
                        recommendation=(
                            "Verify with party confirmation. Review credit terms "
                            "and collection history. Assess need for provision."
                        ),
                    ))
        return findings


class CreditorsWithDebitBalance(AuditRule):
    """AP_002: Sundry creditors with debit balance (advance/overpayment)."""

    rule_id = "AP_002"
    title = "Creditor with Debit Balance"
    category = "Receivables & Payables"
    default_severity = Severity.MEDIUM
    description = (
        "Identifies sundry creditor ledgers showing debit balances, which "
        "may indicate advances paid or overpayments to vendors."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        creditor_ledgers = ctx.get_ledgers_in_group_recursive("Sundry Creditors")

        for ledger in creditor_ledgers:
            # Creditor should have credit balance. Debit balance = advance/overpayment
            if ledger.closing_balance > Decimal("0"):
                balance = ledger.closing_balance
                findings.append(self.finding(
                    title=(
                        f"Creditor '{ledger.name}' has debit balance: "
                        f"₹{balance:,.2f}"
                    ),
                    description=(
                        f"Creditor '{ledger.name}' shows a debit balance of "
                        f"₹{balance:,.2f} instead of the expected credit balance. "
                        f"This typically indicates an advance payment or "
                        f"overpayment to the vendor."
                    ),
                    ledger_name=ledger.name,
                    amount=balance,
                    recommendation=(
                        "Verify if this represents an advance to vendor. "
                        "If so, reclassify as 'Advance to Suppliers' under "
                        "Current Assets. If overpayment, initiate recovery."
                    ),
                ))
        return findings


class ReceivablesExceedRevenue(AuditRule):
    """AP_003: Total trade receivables exceed annual revenue."""

    rule_id = "AP_003"
    title = "Trade Receivables Exceed Revenue"
    category = "Receivables & Payables"
    default_severity = Severity.HIGH
    description = (
        "Checks if total trade receivables exceed total revenue, which is "
        "highly unusual and indicates potential revenue recognition issues."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        debtor_ledgers = ctx.get_ledgers_in_group_recursive("Sundry Debtors")
        revenue_ledgers = ctx.get_ledgers_in_group_recursive("Sales Accounts")

        total_debtors = sum(abs(l.closing_balance) for l in debtor_ledgers)
        total_revenue = sum(abs(l.closing_balance) for l in revenue_ledgers)

        if total_revenue > 0 and total_debtors > total_revenue:
            ratio = (total_debtors / total_revenue * 100) if total_revenue > 0 else 0
            findings.append(self.finding(
                title=(
                    f"Trade receivables (₹{total_debtors:,.2f}) exceed "
                    f"revenue (₹{total_revenue:,.2f})"
                ),
                description=(
                    f"Total trade receivables of ₹{total_debtors:,.2f} are "
                    f"{ratio:.1f}% of annual revenue (₹{total_revenue:,.2f}). "
                    f"Receivables exceeding revenue is highly unusual and may "
                    f"indicate fictitious revenue, collectability issues, or "
                    f"balances carried from prior years."
                ),
                severity=Severity.HIGH,
                amount=total_debtors - total_revenue,
                recommendation=(
                    "Perform detailed aging analysis. Verify top 10 debtors "
                    "with confirmations. Review revenue recognition policy. "
                    "Assess adequacy of provision for doubtful debts."
                ),
                reference="SA 505 / SA 240 (Fraud indicators)",
            ))
        return findings


class ProvisionForDoubtfulDebts(AuditRule):
    """AP_004: Provision for doubtful debts adequacy check."""

    rule_id = "AP_004"
    title = "Doubtful Debts Provision Check"
    category = "Receivables & Payables"
    default_severity = Severity.MEDIUM
    description = (
        "Checks whether a provision for doubtful debts exists when there "
        "are significant trade receivables."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        debtor_ledgers = ctx.get_ledgers_in_group_recursive("Sundry Debtors")
        total_debtors = sum(abs(l.closing_balance) for l in debtor_ledgers)

        if total_debtors < Decimal("100000"):
            return findings

        # Look for provision ledger
        provision_keywords = (
            "provision for doubtful", "provision for bad",
            "allowance for doubtful", "bad debts provision",
        )
        has_provision = False
        provision_amount = Decimal("0")

        for ledger in ctx.ledgers:
            name_lower = ledger.name.lower()
            if any(kw in name_lower for kw in provision_keywords):
                has_provision = True
                provision_amount += abs(ledger.closing_balance)

        if not has_provision:
            findings.append(self.finding(
                title=(
                    f"No provision for doubtful debts against "
                    f"₹{total_debtors:,.2f} receivables"
                ),
                description=(
                    f"Total trade receivables are ₹{total_debtors:,.2f} but no "
                    f"provision for doubtful debts has been identified. As per "
                    f"AS-29 and prudence principle, an adequate provision should "
                    f"be maintained for receivables that may not be collectible."
                ),
                amount=total_debtors,
                recommendation=(
                    "Assess the collectability of each debtor. Create a provision "
                    "for doubtful debts based on aging analysis: typically 25% for "
                    "6-12 months, 50% for 1-2 years, and 100% for >2 years old."
                ),
                reference="AS-29 / Ind AS 37 (Provisions)",
            ))
        return findings


class CreditorBalancesUnconfirmed(AuditRule):
    """AP_005: Large creditor balances flag for confirmation."""

    rule_id = "AP_005"
    title = "Large Creditor Balances Require Confirmation"
    category = "Receivables & Payables"
    default_severity = Severity.INFO
    description = (
        "Flags creditor balances above a threshold that should be confirmed "
        "with external parties as per SA 505."
    )

    THRESHOLD = Decimal("500000")

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        creditor_ledgers = ctx.get_ledgers_in_group_recursive("Sundry Creditors")

        large_creditors = []
        for ledger in creditor_ledgers:
            balance = abs(ledger.closing_balance)
            if balance > self.THRESHOLD:
                large_creditors.append((ledger.name, balance))

        if large_creditors:
            total = sum(b for _, b in large_creditors)
            names = ", ".join(name for name, _ in large_creditors[:5])
            findings.append(self.finding(
                title=(
                    f"{len(large_creditors)} creditors with balances "
                    f">₹5,00,000 (total ₹{total:,.2f})"
                ),
                severity=Severity.INFO,
                description=(
                    f"There are {len(large_creditors)} creditors with individual "
                    f"balances exceeding ₹5,00,000, totalling ₹{total:,.2f}. "
                    f"Top creditors: {names}. These balances should be confirmed "
                    f"with the respective parties (SA 505)."
                ),
                amount=total,
                recommendation=(
                    "Send balance confirmation requests to all major creditors. "
                    "Reconcile any differences. Document the confirmation process "
                    "in audit working papers."
                ),
                reference="SA 505 (External Confirmations)",
            ))
        return findings


class DebitCreditNoteAnomalies(AuditRule):
    """AP_006: Debit/credit notes without corresponding adjustments."""

    rule_id = "AP_006"
    title = "Debit/Credit Note Anomalies"
    category = "Receivables & Payables"
    default_severity = Severity.LOW
    description = (
        "Checks for debit note and credit note vouchers that may need "
        "verification for proper accounting treatment."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        dn_vouchers = ctx.get_vouchers_by_type("Debit Note")
        cn_vouchers = ctx.get_vouchers_by_type("Credit Note")

        # Flag large debit/credit notes
        large_threshold = Decimal("100000")
        for voucher in dn_vouchers + cn_vouchers:
            if abs(voucher.amount) > large_threshold:
                vtype = "Debit Note" if voucher in dn_vouchers else "Credit Note"
                findings.append(self.finding(
                    title=(
                        f"Large {vtype}: ₹{abs(voucher.amount):,.2f} "
                        f"dated {voucher.date}"
                    ),
                    description=(
                        f"{vtype} #{voucher.voucher_number or 'N/A'} dated "
                        f"{voucher.date} for ₹{abs(voucher.amount):,.2f} to "
                        f"'{voucher.party_name or 'Unknown'}'. Large debit/credit "
                        f"notes should be verified for proper authorization and "
                        f"GST adjustment."
                    ),
                    ledger_name=voucher.party_name,
                    amount=abs(voucher.amount),
                    recommendation=(
                        "Verify the reason for the debit/credit note. "
                        "Ensure proper authorization and supporting documents. "
                        "Check if corresponding GST adjustment has been made in "
                        "GSTR-1/GSTR-3B."
                    ),
                    reference="Section 34, CGST Act 2017",
                ))
        return findings
