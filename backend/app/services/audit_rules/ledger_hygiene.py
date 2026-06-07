"""
Ledger hygiene audit rules.

Rules focused on data quality, classification accuracy, and
ledger maintenance best practices.
"""

from __future__ import annotations

from decimal import Decimal
from difflib import SequenceMatcher

from app.services.audit_rules.base import AuditContext, AuditRule, Finding, Severity


class SuspenseAccountBalance(AuditRule):
    """LED_001: Suspense account with non-zero balance."""

    rule_id = "LED_001"
    title = "Suspense Account Has Balance"
    category = "Ledger Hygiene"
    default_severity = Severity.HIGH
    description = (
        "Checks if any suspense or clearing account has an outstanding "
        "balance that should have been cleared before year-end."
    )

    SUSPENSE_KEYWORDS = (
        "suspense", "clearing", "temporary", "transit",
        "unallocated", "unidentified", "misc.",
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        for ledger in ctx.ledgers:
            name_lower = ledger.name.lower()
            if any(kw in name_lower for kw in self.SUSPENSE_KEYWORDS):
                if abs(ledger.closing_balance) > Decimal("0"):
                    findings.append(self.finding(
                        title=(
                            f"Suspense/clearing account '{ledger.name}' has "
                            f"balance ₹{abs(ledger.closing_balance):,.2f}"
                        ),
                        description=(
                            f"Ledger '{ledger.name}' appears to be a suspense or "
                            f"clearing account with an outstanding balance of "
                            f"₹{abs(ledger.closing_balance):,.2f}. Such accounts "
                            f"should be cleared before year-end."
                        ),
                        ledger_name=ledger.name,
                        amount=abs(ledger.closing_balance),
                        recommendation=(
                            "Investigate the items in this suspense account. "
                            "Identify the correct ledger for each entry and "
                            "pass necessary journal entries to clear the balance "
                            "before finalizing the accounts."
                        ),
                    ))
        return findings


class InactiveLedger(AuditRule):
    """LED_002: Ledger with only opening balance and no transactions."""

    rule_id = "LED_002"
    title = "Inactive Ledger with Opening Balance"
    category = "Ledger Hygiene"
    default_severity = Severity.LOW
    description = (
        "Identifies ledgers that have an opening balance but no transactions "
        "during the year, which may indicate stale or forgotten balances."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        for ledger in ctx.ledgers:
            has_opening = abs(ledger.opening_balance) > Decimal("0")
            no_movement = (
                ledger.opening_balance == ledger.closing_balance
                and abs(ledger.debit_total) == Decimal("0")
                and abs(ledger.credit_total) == Decimal("0")
            )
            if has_opening and no_movement:
                findings.append(self.finding(
                    title=f"Inactive ledger: '{ledger.name}'",
                    description=(
                        f"Ledger '{ledger.name}' (group: {ledger.parent}) has an "
                        f"opening balance of ₹{abs(ledger.opening_balance):,.2f} "
                        f"but no transactions during the year. This stale balance "
                        f"may need to be written off or transferred."
                    ),
                    ledger_name=ledger.name,
                    amount=abs(ledger.opening_balance),
                    recommendation=(
                        "Verify if this ledger is still relevant. "
                        "For receivables/payables, check if the amount is "
                        "recoverable/payable. Consider writing off or "
                        "transferring to appropriate heads."
                    ),
                ))
        return findings


class DuplicateLedgerNames(AuditRule):
    """LED_003: Potentially duplicate ledger names (similarity check)."""

    rule_id = "LED_003"
    title = "Potentially Duplicate Ledger Names"
    category = "Ledger Hygiene"
    default_severity = Severity.LOW
    description = (
        "Identifies ledger pairs with very similar names that may be "
        "duplicates or should be merged."
    )

    SIMILARITY_THRESHOLD = 0.85

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        names = [(l.name, l) for l in ctx.ledgers if abs(l.closing_balance) > 0]
        checked_pairs: set[tuple[str, str]] = set()

        for i, (name_a, ledger_a) in enumerate(names):
            for j, (name_b, ledger_b) in enumerate(names):
                if i >= j:
                    continue
                pair_key = (min(name_a, name_b), max(name_a, name_b))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                similarity = SequenceMatcher(
                    None, name_a.lower(), name_b.lower()
                ).ratio()

                if similarity >= self.SIMILARITY_THRESHOLD and name_a != name_b:
                    findings.append(self.finding(
                        title=(
                            f"Possible duplicate: '{name_a}' ↔ '{name_b}'"
                        ),
                        description=(
                            f"Ledgers '{name_a}' (₹{abs(ledger_a.closing_balance):,.2f}) "
                            f"and '{name_b}' (₹{abs(ledger_b.closing_balance):,.2f}) "
                            f"have {similarity:.0%} name similarity. They may be "
                            f"duplicates that should be merged."
                        ),
                        ledger_name=name_a,
                        amount=abs(ledger_a.closing_balance) + abs(
                            ledger_b.closing_balance
                        ),
                        recommendation=(
                            "Review both ledgers and determine if they represent "
                            "the same party or account. If duplicate, merge the "
                            "ledgers in Tally and re-sync."
                        ),
                    ))
        return findings


class LargeUnclassifiedLedger(AuditRule):
    """LED_004: Unclassified/miscellaneous ledgers with large balances."""

    rule_id = "LED_004"
    title = "Large Balance in Miscellaneous Ledger"
    category = "Ledger Hygiene"
    default_severity = Severity.MEDIUM
    description = (
        "Flags ledgers in generic/miscellaneous groups with large balances "
        "that may need proper classification."
    )

    MISC_KEYWORDS = (
        "miscellaneous", "misc", "sundry", "others", "general",
        "unclassified",
    )
    THRESHOLD = Decimal("50000")

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        for ledger in ctx.ledgers:
            name_lower = ledger.name.lower()
            group_lower = ledger.parent.lower() if ledger.parent else ""
            balance = abs(ledger.closing_balance)

            if balance > self.THRESHOLD:
                is_misc = any(
                    kw in name_lower or kw in group_lower
                    for kw in self.MISC_KEYWORDS
                )
                if is_misc:
                    findings.append(self.finding(
                        title=(
                            f"Large balance ₹{balance:,.2f} in "
                            f"'{ledger.name}'"
                        ),
                        description=(
                            f"Ledger '{ledger.name}' (group: {ledger.parent}) "
                            f"has a balance of ₹{balance:,.2f} and appears to "
                            f"be a miscellaneous or catch-all account. Large "
                            f"balances in such ledgers indicate poor classification."
                        ),
                        ledger_name=ledger.name,
                        amount=balance,
                        recommendation=(
                            "Analyze the transactions in this ledger and "
                            "reclassify them under appropriate specific heads. "
                            "Consider creating dedicated ledgers for recurring "
                            "expense/income types."
                        ),
                    ))
        return findings


class BalanceSignMismatch(AuditRule):
    """LED_005: Ledger balance sign doesn't match expected for its group."""

    rule_id = "LED_005"
    title = "Unexpected Balance Sign"
    category = "Ledger Hygiene"
    default_severity = Severity.MEDIUM
    description = (
        "Detects ledgers where the balance sign is opposite to what's "
        "expected for their account group (e.g., asset with credit balance)."
    )

    # Groups that should normally have debit balances (positive)
    DEBIT_GROUPS = {
        "Fixed Assets", "Current Assets", "Investments",
        "Stock-in-Hand", "Sundry Debtors", "Cash-in-Hand",
        "Bank Accounts", "Deposits (Asset)", "Loans & Advances (Asset)",
    }
    # Groups that should normally have credit balances (negative in some conventions)
    CREDIT_GROUPS = {
        "Capital Account", "Reserves & Surplus", "Secured Loans",
        "Unsecured Loans", "Sundry Creditors", "Bank OD A/c",
        "Current Liabilities", "Provisions",
    }

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        for ledger in ctx.ledgers:
            balance = ledger.closing_balance
            if balance == Decimal("0"):
                continue

            group = ledger.parent

            # Check if debit group has credit balance
            if group in self.DEBIT_GROUPS and balance < Decimal("0"):
                findings.append(self.finding(
                    title=f"Credit balance in asset ledger '{ledger.name}'",
                    description=(
                        f"Ledger '{ledger.name}' under '{group}' has a credit "
                        f"balance of ₹{abs(balance):,.2f}. Asset accounts normally "
                        f"carry debit balances. This may indicate over-credit, "
                        f"incorrect posting, or reclassification needed."
                    ),
                    ledger_name=ledger.name,
                    amount=abs(balance),
                    recommendation=(
                        "Verify the reason for the credit balance. "
                        "Reclassify to appropriate liability group if needed, "
                        "or investigate for posting errors."
                    ),
                ))

            # Check if credit group has debit balance
            if group in self.CREDIT_GROUPS and balance > Decimal("0"):
                findings.append(self.finding(
                    title=f"Debit balance in liability ledger '{ledger.name}'",
                    description=(
                        f"Ledger '{ledger.name}' under '{group}' has a debit "
                        f"balance of ₹{balance:,.2f}. Liability/equity accounts "
                        f"normally carry credit balances."
                    ),
                    ledger_name=ledger.name,
                    amount=abs(balance),
                    recommendation=(
                        "Investigate the cause of the debit balance. "
                        "This may indicate overpayment to a creditor or "
                        "incorrect journal entries."
                    ),
                ))
        return findings


class LedgerWithoutGroup(AuditRule):
    """LED_006: Ledgers without proper parent group mapping."""

    rule_id = "LED_006"
    title = "Ledger Missing Proper Group"
    category = "Ledger Hygiene"
    default_severity = Severity.LOW
    description = (
        "Identifies ledgers that are not mapped to any standard Tally "
        "group, which will cause issues in Schedule III mapping."
    )

    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        known_groups = {g.name for g in ctx.groups}

        for ledger in ctx.ledgers:
            if ledger.parent and ledger.parent not in known_groups:
                findings.append(self.finding(
                    title=f"Ledger '{ledger.name}' has unknown group '{ledger.parent}'",
                    description=(
                        f"Ledger '{ledger.name}' is under group '{ledger.parent}' "
                        f"which is not in the synced group list. This may cause "
                        f"issues with Schedule III mapping and financial statement "
                        f"preparation."
                    ),
                    ledger_name=ledger.name,
                    amount=abs(ledger.closing_balance),
                    recommendation=(
                        "Verify the group assignment in Tally. Ensure the group "
                        "hierarchy is complete and properly synced."
                    ),
                ))
        return findings
