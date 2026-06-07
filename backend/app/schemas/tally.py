"""Tally data schemas — ledger, group, voucher, sync, trial balance."""

from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


class TallyGroupResponse(BaseModel):
    id: str
    name: str
    parent: str | None
    is_revenue: bool

    model_config = {"from_attributes": True}


class TallyLedgerResponse(BaseModel):
    id: str
    name: str
    parent: str
    opening_balance: Decimal
    closing_balance: Decimal
    debit_total: Decimal
    credit_total: Decimal
    gstin: str | None
    pan: str | None

    model_config = {"from_attributes": True}


class TallyVoucherResponse(BaseModel):
    id: str
    voucher_type: str
    voucher_number: str | None
    date: date
    party_name: str | None
    amount: Decimal
    narration: str | None

    model_config = {"from_attributes": True}


class SyncJobResponse(BaseModel):
    id: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    groups_synced: int
    ledgers_synced: int
    vouchers_synced: int
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncTriggerResponse(BaseModel):
    job_id: str
    status: str
    message: str


class TrialBalanceEntry(BaseModel):
    ledger_name: str
    group: str
    opening_balance: Decimal
    debit: Decimal
    credit: Decimal
    closing_balance: Decimal


class TrialBalanceResponse(BaseModel):
    client_id: str
    financial_year: str
    entries: list[TrialBalanceEntry]
    total_debit: Decimal
    total_credit: Decimal
    as_of: datetime
