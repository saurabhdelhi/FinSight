"""
Abstract base class for audit rules and supporting types.

Every audit rule inherits from `AuditRule` and implements `evaluate()`.
The audit engine discovers all subclasses automatically.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.models.tally import TallyGroup, TallyLedger, TallyVoucher


# ── Types ────────────────────────────────────────────────────────────────

class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    """A single audit observation produced by a rule."""

    rule_id: str
    severity: Severity
    category: str
    title: str
    description: str
    ledger_name: str | None = None
    amount: Decimal | None = None
    recommendation: str | None = None
    reference: str | None = None
    details: dict[str, Any] | None = None


@dataclass
class AuditContext:
    """
    Provides all synced data to audit rules for evaluation.
    Pre-loaded from the database before rule execution begins.
    """

    client_id: str
    financial_year: str
    ledgers: list[TallyLedger] = field(default_factory=list)
    groups: list[TallyGroup] = field(default_factory=list)
    vouchers: list[TallyVoucher] = field(default_factory=list)

    # Pre-computed lookups
    _ledger_by_name: dict[str, TallyLedger] = field(
        default_factory=dict, repr=False
    )
    _group_by_name: dict[str, TallyGroup] = field(
        default_factory=dict, repr=False
    )
    _ledgers_by_group: dict[str, list[TallyLedger]] = field(
        default_factory=dict, repr=False
    )

    def build_indexes(self) -> None:
        """Build lookup dictionaries after data is loaded."""
        self._ledger_by_name = {led.name: led for led in self.ledgers}
        self._group_by_name = {grp.name: grp for grp in self.groups}
        for led in self.ledgers:
            self._ledgers_by_group.setdefault(led.parent, []).append(led)

    def get_ledger(self, name: str) -> TallyLedger | None:
        return self._ledger_by_name.get(name)

    def get_group(self, name: str) -> TallyGroup | None:
        return self._group_by_name.get(name)

    def get_ledgers_in_group(self, group_name: str) -> list[TallyLedger]:
        """Get all ledgers directly under a group."""
        return self._ledgers_by_group.get(group_name, [])

    def get_ledgers_in_group_recursive(
        self, group_name: str
    ) -> list[TallyLedger]:
        """Get all ledgers under a group and all its sub-groups."""
        result = list(self._ledgers_by_group.get(group_name, []))
        # Find child groups
        for grp in self.groups:
            if grp.parent == group_name:
                result.extend(self.get_ledgers_in_group_recursive(grp.name))
        return result

    def get_vouchers_by_type(self, voucher_type: str) -> list[TallyVoucher]:
        return [v for v in self.vouchers if v.voucher_type == voucher_type]

    def get_vouchers_for_ledger(self, ledger_name: str) -> list[TallyVoucher]:
        """Get all vouchers that contain entries for a specific ledger."""
        result = []
        for v in self.vouchers:
            for entry in v.entries:
                if entry.ledger_name == ledger_name:
                    result.append(v)
                    break
        return result


# ── Abstract Base Rule ───────────────────────────────────────────────────

# Global registry of all rule classes
_rule_registry: list[type["AuditRule"]] = []


class AuditRule(ABC):
    """
    Abstract base class for all audit rules.

    Subclasses must define class-level attributes (rule_id, title, etc.)
    and implement the `evaluate` method.

    Rules are auto-registered on class creation via __init_subclass__.
    """

    rule_id: str = ""
    title: str = ""
    category: str = ""
    default_severity: Severity = Severity.MEDIUM
    description: str = ""

    def __init_subclass__(cls, **kwargs):
        """Auto-register every concrete subclass."""
        super().__init_subclass__(**kwargs)
        if cls.rule_id:  # Skip abstract intermediates
            _rule_registry.append(cls)

    @abstractmethod
    async def evaluate(self, ctx: AuditContext) -> list[Finding]:
        """
        Execute this rule against the audit context.

        Returns a list of Findings (empty list if the rule passes).
        """
        ...

    def finding(
        self,
        title: str,
        description: str,
        severity: Severity | None = None,
        **kwargs,
    ) -> Finding:
        """Convenience method to create a Finding pre-filled with rule metadata."""
        return Finding(
            rule_id=self.rule_id,
            severity=severity or self.default_severity,
            category=self.category,
            title=title,
            description=description,
            **kwargs,
        )


def get_all_rules() -> list[AuditRule]:
    """Instantiate and return all registered audit rules."""
    return [cls() for cls in _rule_registry]


def get_rule_by_id(rule_id: str) -> AuditRule | None:
    """Get a specific rule instance by its ID."""
    for cls in _rule_registry:
        if cls.rule_id == rule_id:
            return cls()
    return None
