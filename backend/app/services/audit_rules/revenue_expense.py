"""
Revenue & Expense audit rules.

Rules focused on revenue recognition, expense classification,
and year-over-year variance analysis.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.audit_rules.base import AuditContext, AuditRule, Finding, Severity


class UnusualRevenueVariance(AuditRule):
    """REV_001: Unusual revenue spike or dip (>30% variance indicator)."""

    rule_id = "REV_001"
    title = "Unusual Revenue Pattern"
    category = "Revenue & Expense"
    default_severity = Severity.MEDIUM
    description = (
        "Checks for revenue ledgers with unusually large balances or "
        "zero balances that may indicate revenue recognition issues."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        revenue_ledgers = ctx.get_ledgers_in_group_recursive("Sales Accounts")

        if not revenue_ledgers:
            return findings

        # Calculate total revenue and check individual ledger proportions
        total_revenue = sum(abs(l.closing_balance) for l in revenue_ledgers)

        for ledger in revenue_ledgers:
            balance = abs(ledger.closing_balance)
            # Flag ledgers with zero balance (inactive revenue streams)
            if balance == Decimal("0") and abs(ledger.opening_balance) > Decimal("0"):
                findings.append(self.finding(
                    title=f"Revenue stream '{ledger.name}' dropped to zero",
                    description=(
                        f"Revenue ledger '{ledger.name}' had an opening balance "
                        f"of ₹{abs(ledger.opening_balance):,.2f} but shows zero "
                        f"revenue this year. Investigate if this is expected or "
                        f"indicates a cut-off error."
                    ),
                    severity=Severity.HIGH,
                    ledger_name=ledger.name,
                    amount=abs(ledger.opening_balance),
                    recommendation=(
                        "Verify with management if this revenue stream has been "
                        "discontinued. Check for misclassification or posting "
                        "to a different ledger."
                    ),
                ))

            # Flag if a single ledger dominates revenue (>80%)
            if total_revenue > 0 and balance > total_revenue * Decimal("0.8"):
                if len(revenue_ledgers) > 1:
                    findings.append(self.finding(
                        title=f"Revenue concentration risk in '{ledger.name}'",
                        description=(
                            f"Ledger '{ledger.name}' accounts for "
                            f"{(balance / total_revenue * 100):.1f}% of total "
                            f"revenue (₹{balance:,.2f} of ₹{total_revenue:,.2f}). "
                            f"High concentration in a single revenue stream is a "
                            f"business risk."
                        ),
                        severity=Severity.INFO,
                        ledger_name=ledger.name,
                        amount=balance,
                        recommendation=(
                            "Note revenue concentration risk in the audit report. "
                            "Verify the revenue figure with supporting documents."
                        ),
                    ))
        return findings


class RevenueWithoutReceivable(AuditRule):
    """REV_002: Revenue recognized without matching receivable movement."""

    rule_id = "REV_002"
    title = "Revenue-Receivable Mismatch"
    category = "Revenue & Expense"
    default_severity = Severity.MEDIUM
    description = (
        "Compares total revenue with trade receivable movement to identify "
        "potential revenue recognition issues."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []

        # Total revenue
        revenue_ledgers = ctx.get_ledgers_in_group_recursive("Sales Accounts")
        total_revenue = sum(abs(l.closing_balance) for l in revenue_ledgers)

        if total_revenue == 0:
            return findings

        # Total receivables
        debtor_ledgers = ctx.get_ledgers_in_group_recursive("Sundry Debtors")
        total_receivables = sum(abs(l.closing_balance) for l in debtor_ledgers)

        # Receivable days = (Receivables / Revenue) * 365
        if total_revenue > 0:
            receivable_days = (total_receivables / total_revenue) * 365
            if receivable_days > 180:
                findings.append(self.finding(
                    title=f"Trade receivable days: {receivable_days:.0f} days",
                    description=(
                        f"Average trade receivable collection period is "
                        f"{receivable_days:.0f} days (Receivables: "
                        f"₹{total_receivables:,.2f}, Revenue: "
                        f"₹{total_revenue:,.2f}). A collection period exceeding "
                        f"180 days warrants investigation into revenue recognition "
                        f"and collectability."
                    ),
                    amount=total_receivables,
                    recommendation=(
                        "Review aging of trade receivables. Verify if provision "
                        "for doubtful debts is adequate. Check for revenue "
                        "recognized but not yet billed."
                    ),
                    reference="SA 240 / Ind AS 115",
                ))
        return findings


class CapitalExpenseMisclassified(AuditRule):
    """EXP_001: Capital expenditure potentially misclassified as revenue."""

    rule_id = "EXP_001"
    title = "Potential Capital Expenditure Misclassification"
    category = "Revenue & Expense"
    default_severity = Severity.HIGH
    description = (
        "Scans expense ledgers for keywords that suggest capital expenditure "
        "incorrectly booked as revenue expense."
    )

    CAPITAL_KEYWORDS = (
        "furniture", "computer", "laptop", "vehicle", "machinery",
        "equipment", "plant", "renovation", "construction",
        "air conditioner", "ac purchase", "software license",
        "server", "printer",
    )
    THRESHOLD = Decimal("25000")  # Capital threshold

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        expense_groups = ["Indirect Expenses", "Direct Expenses", "Misc. Expenses (Asset)"]
        expense_ledgers = []
        for grp in expense_groups:
            expense_ledgers.extend(ctx.get_ledgers_in_group_recursive(grp))

        for ledger in expense_ledgers:
            name_lower = ledger.name.lower()
            balance = abs(ledger.closing_balance)
            if balance > self.THRESHOLD:
                for kw in self.CAPITAL_KEYWORDS:
                    if kw in name_lower:
                        findings.append(self.finding(
                            title=(
                                f"Possible capital expense in '{ledger.name}': "
                                f"₹{balance:,.2f}"
                            ),
                            description=(
                                f"Expense ledger '{ledger.name}' (₹{balance:,.2f}) "
                                f"contains keyword '{kw}' suggesting this may be "
                                f"a capital expenditure that should be capitalized "
                                f"as a fixed asset rather than expensed."
                            ),
                            ledger_name=ledger.name,
                            amount=balance,
                            recommendation=(
                                "Review the nature of this expenditure. If it provides "
                                "benefits for more than one year, it should be "
                                "capitalized and depreciated. Reclassify if needed."
                            ),
                            reference="AS-10 / Ind AS 16 (Property, Plant & Equipment)",
                        ))
                        break  # One finding per ledger
        return findings


class RelatedPartyTransaction(AuditRule):
    """EXP_002: Related party transaction detection."""

    rule_id = "EXP_002"
    title = "Potential Related Party Transaction"
    category = "Revenue & Expense"
    default_severity = Severity.MEDIUM
    description = (
        "Identifies ledgers with common keywords that may indicate related "
        "party transactions requiring disclosure under AS-18/Ind AS 24."
    )

    RP_KEYWORDS = (
        "director", "partner", "promoter", "relative",
        "associate", "subsidiary", "holding", "sister concern",
        "family", "proprietor",
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        for ledger in ctx.ledgers:
            name_lower = ledger.name.lower()
            balance = abs(ledger.closing_balance)
            if balance > Decimal("0"):
                for kw in self.RP_KEYWORDS:
                    if kw in name_lower:
                        findings.append(self.finding(
                            title=f"Potential related party: '{ledger.name}'",
                            description=(
                                f"Ledger '{ledger.name}' (balance ₹{balance:,.2f}) "
                                f"may represent a related party transaction based on "
                                f"keyword '{kw}'. Related party transactions require "
                                f"disclosure under AS-18/Ind AS 24 and may need "
                                f"Board/shareholder approval."
                            ),
                            ledger_name=ledger.name,
                            amount=balance,
                            recommendation=(
                                "Confirm if this is a related party as defined "
                                "under Section 2(76) of Companies Act. If yes, "
                                "ensure proper disclosure in notes to accounts and "
                                "compliance with Section 188 (if applicable)."
                            ),
                            reference="AS-18 / Ind AS 24 / Section 188, Companies Act",
                        ))
                        break
        return findings


class ExpenseRatioAnomaly(AuditRule):
    """EXP_003: Expense ratio anomaly compared to revenue."""

    rule_id = "EXP_003"
    title = "Expense Ratio Anomaly"
    category = "Revenue & Expense"
    default_severity = Severity.LOW
    description = (
        "Checks if any single indirect expense exceeds 25% of total revenue, "
        "which may indicate misclassification or unusual spending."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        revenue_ledgers = ctx.get_ledgers_in_group_recursive("Sales Accounts")
        total_revenue = sum(abs(l.closing_balance) for l in revenue_ledgers)
        if total_revenue == 0:
            return findings

        expense_ledgers = ctx.get_ledgers_in_group_recursive("Indirect Expenses")
        for ledger in expense_ledgers:
            balance = abs(ledger.closing_balance)
            if balance > total_revenue * Decimal("0.25"):
                ratio = (balance / total_revenue * 100) if total_revenue > 0 else 0
                findings.append(self.finding(
                    title=(
                        f"High expense ratio: '{ledger.name}' is "
                        f"{ratio:.1f}% of revenue"
                    ),
                    description=(
                        f"Indirect expense '{ledger.name}' (₹{balance:,.2f}) is "
                        f"{ratio:.1f}% of total revenue (₹{total_revenue:,.2f}). "
                        f"This unusually high ratio warrants investigation."
                    ),
                    ledger_name=ledger.name,
                    amount=balance,
                    recommendation=(
                        "Analyze the composition of this expense. "
                        "Verify with supporting documents. "
                        "Compare with industry benchmarks."
                    ),
                ))
        return findings


class PersonalExpenseDetection(AuditRule):
    """EXP_004: Personal expenses booked under business head."""

    rule_id = "EXP_004"
    title = "Potential Personal Expense"
    category = "Revenue & Expense"
    default_severity = Severity.MEDIUM
    description = (
        "Identifies expense ledgers with keywords suggesting personal "
        "expenses that are not deductible for business purposes."
    )

    PERSONAL_KEYWORDS = (
        "personal", "drawings", "household", "domestic",
        "private", "life insurance premium", "school fee",
        "medical personal", "club membership",
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        expense_groups = ["Indirect Expenses", "Direct Expenses"]
        expense_ledgers = []
        for grp in expense_groups:
            expense_ledgers.extend(ctx.get_ledgers_in_group_recursive(grp))

        for ledger in expense_ledgers:
            name_lower = ledger.name.lower()
            balance = abs(ledger.closing_balance)
            if balance > Decimal("0"):
                for kw in self.PERSONAL_KEYWORDS:
                    if kw in name_lower:
                        findings.append(self.finding(
                            title=f"Potential personal expense: '{ledger.name}'",
                            description=(
                                f"Expense ledger '{ledger.name}' (₹{balance:,.2f}) "
                                f"may contain personal expenses that are not "
                                f"deductible under the Income Tax Act."
                            ),
                            ledger_name=ledger.name,
                            amount=balance,
                            recommendation=(
                                "Review the nature of expenses in this ledger. "
                                "Personal expenses should be disallowed for tax "
                                "purposes and may need to be reclassified as "
                                "drawings or director's remuneration."
                            ),
                            reference="Section 37(1), Income Tax Act 1961",
                        ))
                        break
        return findings
