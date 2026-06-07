"""Tests for the audit engine and rules."""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from app.services.audit_rules.base import AuditContext, get_all_rules, Severity


def _make_ledger(name, parent, closing_balance, opening_balance=0, debit_total=0, credit_total=0):
    """Create a mock ledger for testing."""
    ledger = MagicMock()
    ledger.name = name
    ledger.parent = parent
    ledger.closing_balance = Decimal(str(closing_balance))
    ledger.opening_balance = Decimal(str(opening_balance))
    ledger.debit_total = Decimal(str(debit_total))
    ledger.credit_total = Decimal(str(credit_total))
    return ledger


def _make_group(name, parent=None, is_revenue=False):
    """Create a mock group for testing."""
    group = MagicMock()
    group.name = name
    group.parent = parent
    group.is_revenue = is_revenue
    return group


def _make_voucher(voucher_type, amount, party_name=None, date="2025-12-01",
                  voucher_number="001", entries=None):
    """Create a mock voucher for testing."""
    voucher = MagicMock()
    voucher.voucher_type = voucher_type
    voucher.amount = Decimal(str(amount))
    voucher.party_name = party_name
    voucher.date = date
    voucher.voucher_number = voucher_number
    voucher.entries = entries or []
    voucher.is_cancelled = False
    return voucher


def _make_entry(ledger_name, amount, is_debit):
    entry = MagicMock()
    entry.ledger_name = ledger_name
    entry.amount = Decimal(str(abs(amount)))
    entry.is_debit = is_debit
    return entry


class TestRuleDiscovery:
    """Verify that all 30 rules are discovered."""

    def test_all_rules_registered(self):
        # Import to trigger registration
        import app.services.audit_rules  # noqa: F401
        rules = get_all_rules()
        assert len(rules) >= 30, f"Expected 30+ rules, got {len(rules)}"

    def test_rule_ids_unique(self):
        import app.services.audit_rules  # noqa: F401
        rules = get_all_rules()
        ids = [r.rule_id for r in rules]
        assert len(ids) == len(set(ids)), "Duplicate rule IDs found"

    def test_all_rules_have_metadata(self):
        import app.services.audit_rules  # noqa: F401
        rules = get_all_rules()
        for rule in rules:
            assert rule.rule_id, f"Rule missing rule_id: {rule}"
            assert rule.title, f"Rule {rule.rule_id} missing title"
            assert rule.category, f"Rule {rule.rule_id} missing category"
            assert rule.description, f"Rule {rule.rule_id} missing description"


class TestCashRules:
    """Test cash & bank audit rules."""

    @pytest.mark.asyncio
    async def test_cash_001_high_balance(self):
        """CASH_001 should flag cash balance > ₹2L."""
        from app.services.audit_rules.cash_bank import CashBalanceExceedsLimit

        ctx = AuditContext(client_id="test", financial_year="2025-2026")
        ctx._ledgers_by_group["Cash-in-Hand"] = [
            _make_ledger("Cash", "Cash-in-Hand", 500000),
        ]
        ctx._ledger_by_name = {"Cash": ctx._ledgers_by_group["Cash-in-Hand"][0]}

        rule = CashBalanceExceedsLimit()
        findings = await rule.evaluate(ctx)

        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH
        assert "500,000" in findings[0].title

    @pytest.mark.asyncio
    async def test_cash_004_negative_balance(self):
        """CASH_004 should flag negative cash balance."""
        from app.services.audit_rules.cash_bank import NegativeCashBalance

        ctx = AuditContext(client_id="test", financial_year="2025-2026")
        ctx._ledgers_by_group["Cash-in-Hand"] = [
            _make_ledger("Petty Cash", "Cash-in-Hand", -15000),
        ]

        rule = NegativeCashBalance()
        findings = await rule.evaluate(ctx)

        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL


class TestLedgerHygieneRules:
    """Test ledger hygiene rules."""

    @pytest.mark.asyncio
    async def test_led_001_suspense_account(self):
        """LED_001 should flag suspense accounts with balance."""
        from app.services.audit_rules.ledger_hygiene import SuspenseAccountBalance

        ctx = AuditContext(client_id="test", financial_year="2025-2026")
        ctx.ledgers = [
            _make_ledger("Suspense Account", "Current Assets", 75000),
            _make_ledger("Sales", "Sales Accounts", 100000),
        ]

        rule = SuspenseAccountBalance()
        findings = await rule.evaluate(ctx)

        assert len(findings) == 1
        assert "Suspense" in findings[0].title
