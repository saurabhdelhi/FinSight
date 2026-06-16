"""
MCA Schedule III Mapper.

Maps Tally ledger data (via group hierarchy) to the MCA Schedule III
format (Division I — General Companies) for Balance Sheet and
Statement of Profit & Loss.

The mapping uses Tally's built-in group structure as the primary key,
with keyword-based fallback for unmapped ledgers.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NoSyncDataError
from app.models.client import TallyClient
from app.models.report import ScheduleIIIMapping, ScheduleSection
from app.models.tally import TallyLedger, TallyGroup

logger = logging.getLogger(__name__)


# ── Tally Group → Schedule III Mapping Table ─────────────────────────────
# Format: tally_group -> (schedule_iii_line, category, section, sort_order)

TALLY_GROUP_MAPPING: dict[str, tuple[str, str, ScheduleSection, int]] = {
    # ═══════════════════════════════════════════════════════════════
    # BALANCE SHEET — EQUITY & LIABILITIES
    # ═══════════════════════════════════════════════════════════════
    "Capital Account": (
        "Share Capital", "Shareholders' Funds",
        ScheduleSection.BALANCE_SHEET, 100,
    ),
    "Reserves & Surplus": (
        "Reserves and Surplus", "Shareholders' Funds",
        ScheduleSection.BALANCE_SHEET, 110,
    ),
    "Share Capital": (
        "Share Capital", "Shareholders' Funds",
        ScheduleSection.BALANCE_SHEET, 100,
    ),

    # Non-Current Liabilities
    "Secured Loans": (
        "Long-term Borrowings", "Non-Current Liabilities",
        ScheduleSection.BALANCE_SHEET, 200,
    ),
    "Unsecured Loans": (
        "Long-term Borrowings", "Non-Current Liabilities",
        ScheduleSection.BALANCE_SHEET, 210,
    ),
    "Loans (Liability)": (
        "Long-term Borrowings", "Non-Current Liabilities",
        ScheduleSection.BALANCE_SHEET, 220,
    ),

    # Current Liabilities
    "Bank OD A/c": (
        "Short-term Borrowings", "Current Liabilities",
        ScheduleSection.BALANCE_SHEET, 300,
    ),
    "Sundry Creditors": (
        "Trade Payables", "Current Liabilities",
        ScheduleSection.BALANCE_SHEET, 310,
    ),
    "Duties & Taxes": (
        "Other Current Liabilities", "Current Liabilities",
        ScheduleSection.BALANCE_SHEET, 320,
    ),
    "Current Liabilities": (
        "Other Current Liabilities", "Current Liabilities",
        ScheduleSection.BALANCE_SHEET, 330,
    ),
    "Provisions": (
        "Short-term Provisions", "Current Liabilities",
        ScheduleSection.BALANCE_SHEET, 340,
    ),

    # ═══════════════════════════════════════════════════════════════
    # BALANCE SHEET — ASSETS
    # ═══════════════════════════════════════════════════════════════

    # Non-Current Assets
    "Fixed Assets": (
        "Property, Plant and Equipment", "Non-Current Assets",
        ScheduleSection.BALANCE_SHEET, 400,
    ),
    "Investments": (
        "Non-current Investments", "Non-Current Assets",
        ScheduleSection.BALANCE_SHEET, 410,
    ),
    "Loans & Advances (Asset)": (
        "Long-term Loans and Advances", "Non-Current Assets",
        ScheduleSection.BALANCE_SHEET, 420,
    ),
    "Misc. Expenses (Asset)": (
        "Other Non-current Assets", "Non-Current Assets",
        ScheduleSection.BALANCE_SHEET, 430,
    ),

    # Current Assets
    "Stock-in-Hand": (
        "Inventories", "Current Assets",
        ScheduleSection.BALANCE_SHEET, 500,
    ),
    "Sundry Debtors": (
        "Trade Receivables", "Current Assets",
        ScheduleSection.BALANCE_SHEET, 510,
    ),
    "Cash-in-Hand": (
        "Cash and Cash Equivalents", "Current Assets",
        ScheduleSection.BALANCE_SHEET, 520,
    ),
    "Bank Accounts": (
        "Cash and Cash Equivalents", "Current Assets",
        ScheduleSection.BALANCE_SHEET, 530,
    ),
    "Deposits (Asset)": (
        "Short-term Loans and Advances", "Current Assets",
        ScheduleSection.BALANCE_SHEET, 540,
    ),
    "Current Assets": (
        "Other Current Assets", "Current Assets",
        ScheduleSection.BALANCE_SHEET, 550,
    ),

    # ═══════════════════════════════════════════════════════════════
    # PROFIT & LOSS
    # ═══════════════════════════════════════════════════════════════

    # Revenue
    "Sales Accounts": (
        "Revenue from Operations", "Revenue",
        ScheduleSection.PROFIT_AND_LOSS, 600,
    ),
    "Direct Incomes": (
        "Other Income", "Revenue",
        ScheduleSection.PROFIT_AND_LOSS, 610,
    ),
    "Indirect Incomes": (
        "Other Income", "Revenue",
        ScheduleSection.PROFIT_AND_LOSS, 620,
    ),

    # Expenses
    "Purchase Accounts": (
        "Purchases of Stock-in-Trade", "Expenses",
        ScheduleSection.PROFIT_AND_LOSS, 700,
    ),
    "Direct Expenses": (
        "Cost of Materials Consumed", "Expenses",
        ScheduleSection.PROFIT_AND_LOSS, 710,
    ),
    "Manufacturing Expenses": (
        "Cost of Materials Consumed", "Expenses",
        ScheduleSection.PROFIT_AND_LOSS, 715,
    ),
    "Indirect Expenses": (
        "Other Expenses", "Expenses",
        ScheduleSection.PROFIT_AND_LOSS, 800,
    ),
}

# Keyword fallback mapping for ledgers whose group isn't in the table
KEYWORD_FALLBACK: list[tuple[list[str], str, str, ScheduleSection, int]] = [
    (["salary", "wages", "staff", "employee", "bonus", "gratuity"],
     "Employee Benefits Expense", "Expenses", ScheduleSection.PROFIT_AND_LOSS, 720),
    (["interest", "finance charge", "bank charge", "processing fee"],
     "Finance Costs", "Expenses", ScheduleSection.PROFIT_AND_LOSS, 730),
    (["depreciation", "amortization", "amortisation"],
     "Depreciation and Amortization Expense", "Expenses", ScheduleSection.PROFIT_AND_LOSS, 740),
    (["rent", "lease"],
     "Other Expenses", "Expenses", ScheduleSection.PROFIT_AND_LOSS, 800),
    (["insurance"],
     "Other Expenses", "Expenses", ScheduleSection.PROFIT_AND_LOSS, 800),
    (["repair", "maintenance"],
     "Other Expenses", "Expenses", ScheduleSection.PROFIT_AND_LOSS, 800),
    (["telephone", "internet", "communication"],
     "Other Expenses", "Expenses", ScheduleSection.PROFIT_AND_LOSS, 800),
    (["travel", "conveyance", "vehicle"],
     "Other Expenses", "Expenses", ScheduleSection.PROFIT_AND_LOSS, 800),
    (["printing", "stationery"],
     "Other Expenses", "Expenses", ScheduleSection.PROFIT_AND_LOSS, 800),
    (["audit fee", "professional fee", "legal", "consultancy"],
     "Other Expenses", "Expenses", ScheduleSection.PROFIT_AND_LOSS, 800),
    (["income tax", "deferred tax"],
     "Tax Expense", "Tax", ScheduleSection.PROFIT_AND_LOSS, 900),
]


class ScheduleIIIMapper:
    """Maps Tally trial balance data to MCA Schedule III format."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_client(self, client_id: str) -> TallyClient:
        result = await self.db.execute(
            select(TallyClient).where(TallyClient.id == client_id)
        )
        client = result.scalar_one_or_none()
        if not client:
            from app.core.exceptions import ClientNotFoundError
            raise ClientNotFoundError(client_id)
        return client

    def _resolve_group_hierarchy(
        self,
        ledger: TallyLedger,
        groups_by_name: dict[str, TallyGroup],
    ) -> str | None:
        """
        Walk up the Tally group hierarchy until we find a group
        in our mapping table.
        """
        current_group = ledger.parent
        visited = set()
        while current_group and current_group not in visited:
            if current_group in TALLY_GROUP_MAPPING:
                return current_group
            visited.add(current_group)
            group = groups_by_name.get(current_group)
            if group and group.parent:
                current_group = group.parent
            else:
                break
        return None

    def _keyword_match(
        self, ledger_name: str
    ) -> tuple[str, str, ScheduleSection, int] | None:
        """Try to match a ledger by name keywords."""
        name_lower = ledger_name.lower()
        for keywords, line, category, section, sort in KEYWORD_FALLBACK:
            if any(kw in name_lower for kw in keywords):
                return (line, category, section, sort)
        return None

    async def map_client(self, client_id: str) -> list[ScheduleIIIMapping]:
        """
        Generate Schedule III mappings for all ledgers of a client.

        Strategy:
        1. Walk up Tally group hierarchy to find a matching group
        2. If not found, use keyword-based fallback on ledger name
        3. Remaining unmapped ledgers get a default "Unclassified" mapping
        """
        client = await self._get_client(client_id)

        # Load ledgers and groups
        result = await self.db.execute(
            select(TallyLedger).where(TallyLedger.client_id == client_id)
        )
        ledgers = list(result.scalars().all())

        result = await self.db.execute(
            select(TallyGroup).where(TallyGroup.client_id == client_id)
        )
        groups = list(result.scalars().all())
        groups_by_name = {g.name: g for g in groups}

        if not ledgers:
            raise NoSyncDataError(client_id)

        # Get existing manual overrides to preserve them
        result = await self.db.execute(
            select(ScheduleIIIMapping).where(
                ScheduleIIIMapping.client_id == client_id,
                ScheduleIIIMapping.is_auto_mapped == False,
            )
        )
        manual_mappings = list(result.scalars().all())
        overridden_ledgers = {m.ledger_name: m for m in manual_mappings}

        # Clear only existing auto-mapped mappings
        await self.db.execute(
            delete(ScheduleIIIMapping).where(
                ScheduleIIIMapping.client_id == client_id,
                ScheduleIIIMapping.is_auto_mapped == True,
            )
        )

        mappings = []
        for ledger in ledgers:
            # Skip zero-balance ledgers (unless they have opening balance)
            if (
                abs(ledger.closing_balance) < Decimal("0.01")
                and abs(ledger.opening_balance) < Decimal("0.01")
            ):
                continue

            # If this ledger has a manual override, preserve it and update its amount to latest closing balance
            if ledger.name in overridden_ledgers:
                m = overridden_ledgers[ledger.name]
                m.amount = ledger.closing_balance
                mappings.append(m)
                continue

            # Strategy 1: Group hierarchy walk
            matched_group = self._resolve_group_hierarchy(ledger, groups_by_name)

            # Special case: Profit & Loss A/c should always map to Reserves and Surplus under Shareholders' Funds
            if ledger.name.lower() in ("profit & loss a/c", "profit and loss", "p&l", "p&l a/c"):
                line = "Reserves and Surplus"
                category = "Shareholders' Funds"
                section = ScheduleSection.BALANCE_SHEET
                sort = 110
                confidence = 100.0
                is_auto = True
            elif matched_group:
                line, category, section, sort = TALLY_GROUP_MAPPING[matched_group]
                confidence = 95.0
                is_auto = True
            else:
                # Strategy 2: Keyword fallback
                kw_match = self._keyword_match(ledger.name)
                if kw_match:
                    line, category, section, sort = kw_match
                    confidence = 70.0
                    is_auto = True
                else:
                    # Strategy 3: Default unclassified
                    line = "Unclassified"
                    category = "Unclassified"
                    section = ScheduleSection.BALANCE_SHEET
                    sort = 999
                    confidence = 0.0
                    is_auto = False

            mapping = ScheduleIIIMapping(
                client_id=client_id,
                ledger_name=ledger.name,
                tally_group=ledger.parent,
                section=section,
                schedule_iii_line=line,
                category=category,
                amount=ledger.closing_balance,
                is_auto_mapped=is_auto,
                mapping_confidence=confidence,
                sort_order=sort,
            )
            self.db.add(mapping)
            mappings.append(mapping)

        await self.db.flush()
        logger.info(
            f"Mapped {len(mappings)} ledgers to Schedule III for client {client_id[:8]}"
        )
        return mappings

    async def get_balance_sheet(self, client_id: str) -> dict[str, Any]:
        """
        Generate a structured Balance Sheet from Schedule III mappings.
        Returns hierarchical data: Category → Line Item → Amount.
        """
        result = await self.db.execute(
            select(ScheduleIIIMapping).where(
                ScheduleIIIMapping.client_id == client_id,
                ScheduleIIIMapping.section == ScheduleSection.BALANCE_SHEET,
            ).order_by(ScheduleIIIMapping.sort_order)
        )
        mappings = list(result.scalars().all())

        if not mappings:
            # Try to generate mappings first
            await self.map_client(client_id)
            result = await self.db.execute(
                select(ScheduleIIIMapping).where(
                    ScheduleIIIMapping.client_id == client_id,
                    ScheduleIIIMapping.section == ScheduleSection.BALANCE_SHEET,
                ).order_by(ScheduleIIIMapping.sort_order)
            )
            mappings = list(result.scalars().all())

        # Aggregate by category → line item
        equity_liabilities: dict[str, dict[str, Decimal]] = {}
        assets: dict[str, dict[str, Decimal]] = {}

        equity_categories = {"Shareholders' Funds", "Non-Current Liabilities", "Current Liabilities"}
        asset_categories = {"Non-Current Assets", "Current Assets"}

        for m in mappings:
            is_equity_liab = m.category in equity_categories
            
            # Normal sign convention:
            # - Equity & Liabilities are normally Credit (positive in Tally)
            # - Assets are normally Debit (negative in Tally)
            val = m.amount if is_equity_liab else -m.amount
            
            target = equity_liabilities if is_equity_liab else assets
            if m.category not in target:
                target[m.category] = {}
            line = m.schedule_iii_line
            target[m.category][line] = target[m.category].get(line, Decimal("0")) + val

        # Calculate totals
        total_el = sum(
            sum(items.values()) for items in equity_liabilities.values()
        )
        total_assets = sum(
            sum(items.values()) for items in assets.values()
        )

        client = await self._get_client(client_id)

        return {
            "client_id": client_id,
            "financial_year": client.financial_year,
            "equity_and_liabilities": equity_liabilities,
            "assets": assets,
            "total_equity_liabilities": total_el,
            "total_assets": total_assets,
            "is_balanced": abs(total_el - total_assets) < Decimal("1.00"),
        }

    async def get_profit_and_loss(self, client_id: str) -> dict[str, Any]:
        """
        Generate a structured P&L Statement from Schedule III mappings.
        """
        result = await self.db.execute(
            select(ScheduleIIIMapping).where(
                ScheduleIIIMapping.client_id == client_id,
                ScheduleIIIMapping.section == ScheduleSection.PROFIT_AND_LOSS,
            ).order_by(ScheduleIIIMapping.sort_order)
        )
        mappings = list(result.scalars().all())

        if not mappings:
            await self.map_client(client_id)
            result = await self.db.execute(
                select(ScheduleIIIMapping).where(
                    ScheduleIIIMapping.client_id == client_id,
                    ScheduleIIIMapping.section == ScheduleSection.PROFIT_AND_LOSS,
                ).order_by(ScheduleIIIMapping.sort_order)
            )
            mappings = list(result.scalars().all())

        revenue: dict[str, Decimal] = {}
        expenses: dict[str, Decimal] = {}
        tax: dict[str, Decimal] = {}

        for m in mappings:
            if m.category == "Revenue":
                revenue[m.schedule_iii_line] = revenue.get(
                    m.schedule_iii_line, Decimal("0")
                ) + abs(m.amount)
            elif m.category == "Tax":
                tax[m.schedule_iii_line] = tax.get(
                    m.schedule_iii_line, Decimal("0")
                ) + abs(m.amount)
            else:
                expenses[m.schedule_iii_line] = expenses.get(
                    m.schedule_iii_line, Decimal("0")
                ) + abs(m.amount)

        total_revenue = sum(revenue.values())
        total_expenses = sum(expenses.values())
        total_tax = sum(tax.values())
        profit_before_tax = total_revenue - total_expenses
        net_profit = profit_before_tax - total_tax

        client = await self._get_client(client_id)

        return {
            "client_id": client_id,
            "financial_year": client.financial_year,
            "revenue": revenue,
            "expenses": expenses,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "profit_before_tax": profit_before_tax,
            "tax_expense": total_tax,
            "net_profit": net_profit,
        }

    async def override_mapping(
        self,
        client_id: str,
        ledger_name: str,
        schedule_iii_line: str,
        category: str,
        section: str,
        sub_category: str | None = None,
    ) -> ScheduleIIIMapping:
        """Manually override a Schedule III mapping for a ledger."""
        result = await self.db.execute(
            select(ScheduleIIIMapping).where(
                ScheduleIIIMapping.client_id == client_id,
                ScheduleIIIMapping.ledger_name == ledger_name,
            )
        )
        mapping = result.scalar_one_or_none()
        if mapping:
            mapping.schedule_iii_line = schedule_iii_line
            mapping.category = category
            mapping.sub_category = sub_category
            mapping.section = ScheduleSection(section)
            mapping.is_auto_mapped = False
            mapping.mapping_confidence = 100.0
        else:
            mapping = ScheduleIIIMapping(
                client_id=client_id,
                ledger_name=ledger_name,
                tally_group="",
                section=ScheduleSection(section),
                schedule_iii_line=schedule_iii_line,
                category=category,
                sub_category=sub_category,
                is_auto_mapped=False,
                mapping_confidence=100.0,
            )
            self.db.add(mapping)

        await self.db.flush()
        return mapping
