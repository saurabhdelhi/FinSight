"""Report and Schedule III schemas."""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class ScheduleIIIMappingResponse(BaseModel):
    id: str
    ledger_name: str
    tally_group: str
    section: str
    schedule_iii_line: str
    category: str
    sub_category: str | None
    amount: Decimal
    is_auto_mapped: bool
    mapping_confidence: float | None

    model_config = {"from_attributes": True}


class MappingOverrideRequest(BaseModel):
    ledger_name: str
    schedule_iii_line: str
    category: str
    sub_category: str | None = None
    section: str  # "balance_sheet" or "profit_and_loss"


class ScheduleIIILineItem(BaseModel):
    line_item: str
    amount: Decimal
    sub_items: list["ScheduleIIILineItem"] = []
    note_ref: str | None = None


class BalanceSheetResponse(BaseModel):
    client_id: str
    financial_year: str
    equity_and_liabilities: list[ScheduleIIILineItem]
    assets: list[ScheduleIIILineItem]
    total_equity_liabilities: Decimal
    total_assets: Decimal
    is_balanced: bool


class ProfitAndLossResponse(BaseModel):
    client_id: str
    financial_year: str
    revenue: list[ScheduleIIILineItem]
    expenses: list[ScheduleIIILineItem]
    total_revenue: Decimal
    total_expenses: Decimal
    profit_before_tax: Decimal
    tax_expense: Decimal
    net_profit: Decimal


class ReportGenerateRequest(BaseModel):
    report_type: str  # "audit_report", "financial_statements", "combined"
    report_format: str  # "xlsx" or "pdf"


class ReportResponse(BaseModel):
    id: str
    report_type: str
    report_format: str
    file_name: str
    file_size_bytes: int | None
    generated_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int
