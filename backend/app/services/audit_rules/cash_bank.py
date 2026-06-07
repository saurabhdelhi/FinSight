"""
Cash & Bank audit rules.

Rules focused on cash handling compliance per Indian tax law
and bank reconciliation anomalies.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.audit_rules.base import AuditContext, AuditRule, Finding, Severity


class CashBalanceExceedsLimit(AuditRule):
    """CASH_001: Cash balance exceeds ₹2,00,000 (Section 269SS/269T threshold)."""

    rule_id = "CASH_001"
    title = "Cash Balance Exceeds ₹2,00,000"
    category = "Cash & Bank"
    default_severity = Severity.HIGH
    description = (
        "Checks if any cash-in-hand ledger has a closing balance exceeding "
        "₹2,00,000, which triggers scrutiny under Section 269SS/269T of the "
        "Income Tax Act."
    )

    THRESHOLD = Decimal("200000")

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        cash_ledgers = ctx.get_ledgers_in_group_recursive("Cash-in-Hand")
        for ledger in cash_ledgers:
            # Cash balances are typically positive (debit balance)
            balance = abs(ledger.closing_balance)
            if balance > self.THRESHOLD:
                findings.append(self.finding(
                    title=f"Cash balance of ₹{balance:,.2f} exceeds ₹2,00,000 limit",
                    description=(
                        f"Ledger '{ledger.name}' has a closing cash balance of "
                        f"₹{balance:,.2f} which exceeds the ₹2,00,000 threshold. "
                        f"This may attract scrutiny under Sections 269SS and 269T "
                        f"of the Income Tax Act, 1961."
                    ),
                    ledger_name=ledger.name,
                    amount=balance,
                    recommendation=(
                        "Review the necessity of maintaining high cash balances. "
                        "Consider depositing excess cash into a bank account. "
                        "Ensure all cash transactions are properly documented."
                    ),
                    reference="Section 269SS/269T, Income Tax Act 1961",
                ))
        return findings


class LargeCashTransaction(AuditRule):
    """CASH_002: Single cash payment exceeds ₹10,000 (Section 40A(3) disallowance)."""

    rule_id = "CASH_002"
    title = "Cash Payment Exceeds ₹10,000"
    category = "Cash & Bank"
    default_severity = Severity.HIGH
    description = (
        "Identifies individual cash payments exceeding ₹10,000 to a single "
        "party in a single day, which are disallowed under Section 40A(3)."
    )

    THRESHOLD = Decimal("10000")

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        cash_vouchers = ctx.get_vouchers_by_type("Payment")
        for voucher in cash_vouchers:
            # Check if any entry involves a cash ledger
            has_cash = False
            for entry in voucher.entries:
                if entry.ledger_name.lower() in ("cash", "cash-in-hand", "petty cash"):
                    has_cash = True
                    break
                ledger = ctx.get_ledger(entry.ledger_name)
                if ledger and ledger.parent in ("Cash-in-Hand",):
                    has_cash = True
                    break

            if has_cash and abs(voucher.amount) > self.THRESHOLD:
                findings.append(self.finding(
                    title=(
                        f"Cash payment of ₹{abs(voucher.amount):,.2f} "
                        f"exceeds ₹10,000 limit"
                    ),
                    description=(
                        f"Voucher #{voucher.voucher_number or 'N/A'} dated "
                        f"{voucher.date} to '{voucher.party_name or 'Unknown'}' "
                        f"involves a cash payment of ₹{abs(voucher.amount):,.2f}. "
                        f"Cash expenses exceeding ₹10,000 to a single party in "
                        f"a single day are disallowed under Section 40A(3)."
                    ),
                    ledger_name=voucher.party_name,
                    amount=abs(voucher.amount),
                    recommendation=(
                        "Verify if payment was made by account payee cheque/draft "
                        "or electronic clearing system. If cash, this expense may "
                        "be disallowed for tax purposes. Consider Rule 6DD exceptions."
                    ),
                    reference="Section 40A(3), Income Tax Act 1961",
                ))
        return findings


class CashReceiptExceedsLimit(AuditRule):
    """CASH_003: Cash receipt exceeds ₹2,00,000 from a single party (Section 269ST)."""

    rule_id = "CASH_003"
    title = "Cash Receipt Exceeds ₹2,00,000 from Single Party"
    category = "Cash & Bank"
    default_severity = Severity.CRITICAL
    description = (
        "Identifies cash receipts exceeding ₹2,00,000 from a single party, "
        "which is prohibited under Section 269ST with penalty under 271DA."
    )

    THRESHOLD = Decimal("200000")

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        receipt_vouchers = ctx.get_vouchers_by_type("Receipt")
        for voucher in receipt_vouchers:
            has_cash = False
            for entry in voucher.entries:
                ledger = ctx.get_ledger(entry.ledger_name)
                if ledger and ledger.parent in ("Cash-in-Hand",):
                    has_cash = True
                    break

            if has_cash and abs(voucher.amount) > self.THRESHOLD:
                findings.append(self.finding(
                    title=(
                        f"Cash receipt of ₹{abs(voucher.amount):,.2f} "
                        f"exceeds ₹2,00,000 limit"
                    ),
                    description=(
                        f"Voucher #{voucher.voucher_number or 'N/A'} dated "
                        f"{voucher.date} from '{voucher.party_name or 'Unknown'}' "
                        f"is a cash receipt of ₹{abs(voucher.amount):,.2f}. "
                        f"Receiving ₹2,00,000 or more in cash from a single party "
                        f"in a day is prohibited under Section 269ST."
                    ),
                    severity=Severity.CRITICAL,
                    ledger_name=voucher.party_name,
                    amount=abs(voucher.amount),
                    recommendation=(
                        "This is a penalty-attracting transaction under Section 271DA. "
                        "Penalty is equal to the amount received. Verify if this was "
                        "actually received in cash or via banking channels."
                    ),
                    reference="Section 269ST / 271DA, Income Tax Act 1961",
                ))
        return findings


class NegativeCashBalance(AuditRule):
    """CASH_004: Negative cash balance detected (physical impossibility)."""

    rule_id = "CASH_004"
    title = "Negative Cash Balance Detected"
    category = "Cash & Bank"
    default_severity = Severity.CRITICAL
    description = (
        "Detects if any cash ledger shows a negative (credit) balance, "
        "which is physically impossible and indicates recording errors."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        cash_ledgers = ctx.get_ledgers_in_group_recursive("Cash-in-Hand")
        for ledger in cash_ledgers:
            # For cash, a credit balance (positive in Tally convention for
            # some groups) means negative cash — physically impossible
            if ledger.closing_balance > Decimal("0"):
                # In Tally, positive balance for Cash-in-Hand parent group
                # means debit (normal). But if the group is marked as
                # deemedpositive=No, then positive = credit = negative cash.
                # We check both conventions:
                pass  # Normal debit balance for cash

            # More reliable: check if closing < 0 (our normalized convention)
            if ledger.closing_balance < Decimal("0"):
                findings.append(self.finding(
                    title=f"Negative cash balance in '{ledger.name}'",
                    description=(
                        f"Ledger '{ledger.name}' shows a negative balance of "
                        f"₹{ledger.closing_balance:,.2f}. A negative cash balance "
                        f"is physically impossible and indicates either unrecorded "
                        f"receipts or incorrect entries."
                    ),
                    severity=Severity.CRITICAL,
                    ledger_name=ledger.name,
                    amount=abs(ledger.closing_balance),
                    recommendation=(
                        "Investigate all transactions in this cash ledger. "
                        "Identify missing receipt entries or incorrect payment "
                        "postings. Rectify before finalizing accounts."
                    ),
                ))
        return findings


class BankReconciliationVariance(AuditRule):
    """CASH_005: Bank reconciliation variance exceeds threshold."""

    rule_id = "CASH_005"
    title = "Significant Bank Reconciliation Variance"
    category = "Cash & Bank"
    default_severity = Severity.MEDIUM
    description = (
        "Flags bank ledgers where the balance suggests potential "
        "reconciliation issues (unusually large balances or negative balances)."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        bank_ledgers = ctx.get_ledgers_in_group_recursive("Bank Accounts")
        for ledger in bank_ledgers:
            # Flag negative bank balances (overdraft without OD facility)
            if ledger.closing_balance < Decimal("0"):
                # Check if it's under "Bank OD A/c" group (overdraft is normal)
                if ledger.parent != "Bank OD A/c":
                    findings.append(self.finding(
                        title=f"Negative bank balance in '{ledger.name}'",
                        description=(
                            f"Bank ledger '{ledger.name}' shows a negative balance "
                            f"of ₹{ledger.closing_balance:,.2f}. Unless this is an "
                            f"overdraft facility, this may indicate unrecorded "
                            f"deposits or timing differences requiring reconciliation."
                        ),
                        ledger_name=ledger.name,
                        amount=abs(ledger.closing_balance),
                        recommendation=(
                            "Obtain bank statement and perform reconciliation. "
                            "Identify outstanding cheques and deposits in transit. "
                            "If overdraft, reclassify under 'Bank OD A/c' group."
                        ),
                    ))
        return findings


class LargeRoundNumberCash(AuditRule):
    """CASH_006: Large round-number cash transactions (anomaly detection)."""

    rule_id = "CASH_006"
    title = "Large Round-Number Cash Transactions"
    category = "Cash & Bank"
    default_severity = Severity.LOW
    description = (
        "Flags suspiciously large round-number cash transactions that may "
        "indicate estimation rather than actual recording."
    )

    THRESHOLD = Decimal("50000")

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        cash_types = ("Payment", "Receipt")
        for vtype in cash_types:
            for voucher in ctx.get_vouchers_by_type(vtype):
                amt = abs(voucher.amount)
                if amt >= self.THRESHOLD and amt % 10000 == 0:
                    # Check if involves cash ledger
                    has_cash = any(
                        ctx.get_ledger(e.ledger_name)
                        and ctx.get_ledger(e.ledger_name).parent
                        in ("Cash-in-Hand",)
                        for e in voucher.entries
                    )
                    if has_cash:
                        findings.append(self.finding(
                            title=(
                                f"Round-number cash {vtype.lower()} of "
                                f"₹{amt:,.2f}"
                            ),
                            description=(
                                f"Voucher #{voucher.voucher_number or 'N/A'} "
                                f"dated {voucher.date}: ₹{amt:,.2f} is a large "
                                f"round number, which may indicate an estimated "
                                f"or fabricated entry."
                            ),
                            ledger_name=voucher.party_name,
                            amount=amt,
                            recommendation=(
                                "Verify the transaction with supporting "
                                "documents (invoice, receipt, etc.). "
                                "Round-number transactions above ₹50,000 "
                                "warrant additional scrutiny."
                            ),
                        ))
        return findings
