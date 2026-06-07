"""
Tally XML response parser.

Parses the XML returned by Tally Prime's HTTP API into typed Python
dataclasses that the sync service can persist to the database.

Handles Tally-specific quirks:
- Amount signs: Tally uses negative for Debit balances in some contexts
- Empty/missing tags
- Nested ALLLEDGERENTRIES.LIST within vouchers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from app.core.exceptions import TallyDataError

logger = logging.getLogger(__name__)


# ── Parsed data classes ──────────────────────────────────────────────────

@dataclass
class ParsedGroup:
    name: str
    parent: str | None = None
    guid: str | None = None
    alter_id: int | None = None
    is_revenue: bool = False
    is_deemedpositive: bool = False
    affects_gross_profit: bool = False
    sort_position: int = 0


@dataclass
class ParsedLedger:
    name: str
    parent: str = ""
    guid: str | None = None
    alter_id: int | None = None
    opening_balance: Decimal = Decimal("0.00")
    closing_balance: Decimal = Decimal("0.00")
    address: str | None = None
    gstin: str | None = None
    pan: str | None = None
    is_bill_wise: bool = False
    is_cost_centres_on: bool = False


@dataclass
class ParsedVoucherEntry:
    ledger_name: str
    amount: Decimal
    is_debit: bool


@dataclass
class ParsedVoucher:
    guid: str | None = None
    alter_id: int | None = None
    voucher_type: str = ""
    voucher_number: str | None = None
    date: str = ""  # YYYYMMDD
    party_name: str | None = None
    amount: Decimal = Decimal("0.00")
    narration: str | None = None
    is_cancelled: bool = False
    is_optional: bool = False
    entries: list[ParsedVoucherEntry] = field(default_factory=list)


@dataclass
class ParsedTrialBalanceEntry:
    ledger_name: str
    group: str
    opening_balance: Decimal = Decimal("0.00")
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    closing_balance: Decimal = Decimal("0.00")


@dataclass
class ParsedCompanyInfo:
    name: str
    formal_name: str | None = None
    address: str | None = None
    email: str | None = None
    starting_from: str | None = None


# ── Helper functions ─────────────────────────────────────────────────────

def _text(element: ET.Element | None, tag: str, default: str = "") -> str:
    """Extract text from a child element, returning default if missing."""
    if element is None:
        return default
    child = element.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _decimal(element: ET.Element | None, tag: str) -> Decimal:
    """Extract a decimal value, handling Tally's various number formats."""
    raw = _text(element, tag, "0")
    # Tally sometimes uses commas and spaces
    raw = raw.replace(",", "").replace(" ", "")
    try:
        return Decimal(raw)
    except InvalidOperation:
        logger.warning(f"Could not parse decimal from '{raw}' in tag '{tag}'")
        return Decimal("0.00")


def _bool(element: ET.Element | None, tag: str) -> bool:
    """Parse Tally's Yes/No boolean fields."""
    val = _text(element, tag, "No").upper()
    return val in ("YES", "TRUE", "1")


def _int(element: ET.Element | None, tag: str, default: int = 0) -> int:
    """Extract an integer value."""
    raw = _text(element, tag, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


# ── Parser class ─────────────────────────────────────────────────────────

class TallyParser:
    """Parses Tally XML responses into typed Python objects."""

    @staticmethod
    def parse_company_info(xml_text: str) -> list[ParsedCompanyInfo]:
        """Parse company list response."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise TallyDataError(f"Failed to parse company XML: {e}")

        companies = []
        # Look for COMPANY elements under various possible paths
        for comp in root.iter("COMPANY"):
            name = _text(comp, "NAME") or comp.text or ""
            if name:
                companies.append(ParsedCompanyInfo(
                    name=name.strip(),
                    formal_name=_text(comp, "FORMALNAME") or None,
                ))

        # Fallback: sometimes it's just a list of company names
        if not companies:
            body = root.find(".//BODY")
            if body is not None:
                for child in body.iter():
                    if child.text and child.text.strip():
                        companies.append(ParsedCompanyInfo(
                            name=child.text.strip()
                        ))

        return companies

    @staticmethod
    def parse_groups(xml_text: str) -> list[ParsedGroup]:
        """Parse group collection response."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise TallyDataError(f"Failed to parse groups XML: {e}")

        groups = []
        for grp_elem in root.iter("GROUP"):
            name = _text(grp_elem, "NAME")
            if not name:
                # Try attribute-based name
                name = grp_elem.get("NAME", "")
            if not name:
                continue

            groups.append(ParsedGroup(
                name=name,
                parent=_text(grp_elem, "PARENT") or None,
                guid=_text(grp_elem, "GUID") or None,
                alter_id=_int(grp_elem, "ALTERID") or None,
                is_revenue=_bool(grp_elem, "ISREVENUE"),
                is_deemedpositive=_bool(grp_elem, "ISDEEMEDPOSITIVE"),
                affects_gross_profit=_bool(grp_elem, "AFFECTSGROSSPROFIT"),
                sort_position=_int(grp_elem, "SORTPOSITION"),
            ))

        logger.info(f"Parsed {len(groups)} groups from Tally")
        return groups

    @staticmethod
    def parse_ledgers(xml_text: str) -> list[ParsedLedger]:
        """Parse ledger collection response."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise TallyDataError(f"Failed to parse ledgers XML: {e}")

        ledgers = []
        for led_elem in root.iter("LEDGER"):
            name = _text(led_elem, "NAME")
            if not name:
                name = led_elem.get("NAME", "")
            if not name:
                continue

            # Address may be a list
            address_parts = []
            for addr_list in led_elem.iter("ADDRESS.LIST"):
                for addr in addr_list.iter("ADDRESS"):
                    if addr.text:
                        address_parts.append(addr.text.strip())

            ledgers.append(ParsedLedger(
                name=name,
                parent=_text(led_elem, "PARENT"),
                guid=_text(led_elem, "GUID") or None,
                alter_id=_int(led_elem, "ALTERID") or None,
                opening_balance=_decimal(led_elem, "OPENINGBALANCE"),
                closing_balance=_decimal(led_elem, "CLOSINGBALANCE"),
                address=", ".join(address_parts) if address_parts else None,
                gstin=_text(led_elem, "PARTYGSTIN") or None,
                pan=_text(led_elem, "INCOMETAXNUMBER") or None,
                is_bill_wise=_bool(led_elem, "ISBILLWISEON"),
                is_cost_centres_on=_bool(led_elem, "ISCOSTCENTRESON"),
            ))

        logger.info(f"Parsed {len(ledgers)} ledgers from Tally")
        return ledgers

    @staticmethod
    def parse_vouchers(xml_text: str) -> list[ParsedVoucher]:
        """Parse voucher collection response with ledger entries."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise TallyDataError(f"Failed to parse vouchers XML: {e}")

        vouchers = []
        for vch_elem in root.iter("VOUCHER"):
            guid = _text(vch_elem, "GUID") or vch_elem.get("GUID")
            date_str = _text(vch_elem, "DATE")

            voucher = ParsedVoucher(
                guid=guid or None,
                alter_id=_int(vch_elem, "ALTERID") or None,
                voucher_type=_text(vch_elem, "VOUCHERTYPENAME"),
                voucher_number=_text(vch_elem, "VOUCHERNUMBER") or None,
                date=date_str,
                party_name=_text(vch_elem, "PARTYLEDGERNAME") or None,
                amount=_decimal(vch_elem, "AMOUNT"),
                narration=_text(vch_elem, "NARRATION") or None,
                is_cancelled=_bool(vch_elem, "ISCANCELLED"),
                is_optional=_bool(vch_elem, "ISOPTIONAL"),
            )

            # Parse ledger entries within the voucher
            for entry_elem in vch_elem.iter("ALLLEDGERENTRIES.LIST"):
                ledger_name = _text(entry_elem, "LEDGERNAME")
                amount = _decimal(entry_elem, "AMOUNT")
                if ledger_name:
                    # In Tally, negative amount = Debit, positive = Credit
                    voucher.entries.append(ParsedVoucherEntry(
                        ledger_name=ledger_name,
                        amount=abs(amount),
                        is_debit=amount < 0,
                    ))

            # Also check LEDGERENTRIES.LIST (alternate tag name)
            for entry_elem in vch_elem.iter("LEDGERENTRIES.LIST"):
                ledger_name = _text(entry_elem, "LEDGERNAME")
                amount = _decimal(entry_elem, "AMOUNT")
                if ledger_name:
                    voucher.entries.append(ParsedVoucherEntry(
                        ledger_name=ledger_name,
                        amount=abs(amount),
                        is_debit=amount < 0,
                    ))

            vouchers.append(voucher)

        logger.info(f"Parsed {len(vouchers)} vouchers from Tally")
        return vouchers

    @staticmethod
    def parse_trial_balance(xml_text: str) -> list[ParsedTrialBalanceEntry]:
        """
        Parse trial balance report.
        The trial balance from Tally comes as a DSPACCNAME / DSPCLBAL report.
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise TallyDataError(f"Failed to parse trial balance XML: {e}")

        entries = []
        # Trial balance entries can appear under various tags
        for entry in root.iter("DSPACCNAME"):
            parent = entry.getparent() if hasattr(entry, 'getparent') else None
            name = entry.text.strip() if entry.text else ""
            if not name:
                continue

            # Try to find the corresponding balance in a sibling element
            # This depends on the exact Tally report format
            entries.append(ParsedTrialBalanceEntry(
                ledger_name=name,
                group="",
            ))

        # If the above didn't work, try an alternate structure
        if not entries:
            for ledger_elem in root.iter("LEDGER"):
                name = _text(ledger_elem, "NAME") or ledger_elem.get("NAME", "")
                if not name:
                    continue
                ob = _decimal(ledger_elem, "OPENINGBALANCE")
                cb = _decimal(ledger_elem, "CLOSINGBALANCE")
                debit = max(Decimal("0"), -ob + cb) if cb > ob else Decimal("0")
                credit = max(Decimal("0"), ob - cb) if ob > cb else Decimal("0")

                entries.append(ParsedTrialBalanceEntry(
                    ledger_name=name,
                    group=_text(ledger_elem, "PARENT"),
                    opening_balance=ob,
                    debit=debit,
                    credit=credit,
                    closing_balance=cb,
                ))

        logger.info(f"Parsed {len(entries)} trial balance entries from Tally")
        return entries
