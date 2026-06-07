"""Schedule III mapping and generated report models."""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, generate_uuid


class ScheduleSection(str, enum.Enum):
    BALANCE_SHEET = "balance_sheet"
    PROFIT_AND_LOSS = "profit_and_loss"


class ReportType(str, enum.Enum):
    AUDIT_REPORT = "audit_report"
    FINANCIAL_STATEMENTS = "financial_statements"
    COMBINED = "combined"


class ReportFormat(str, enum.Enum):
    XLSX = "xlsx"
    PDF = "pdf"


class ScheduleIIIMapping(Base, TimestampMixin):
    """
    Maps a Tally ledger to a specific MCA Schedule III line item.
    Auto-mapped from Tally group hierarchy, with manual override support.
    """

    __tablename__ = "schedule_iii_mappings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    ledger_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tally_group: Mapped[str] = mapped_column(String(255), nullable=False)
    section: Mapped[ScheduleSection] = mapped_column(
        Enum(ScheduleSection), nullable=False
    )
    schedule_iii_line: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # e.g. "Trade Receivables"
    category: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "Current Assets"
    sub_category: Mapped[str | None] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00")
    )
    is_auto_mapped: Mapped[bool] = mapped_column(Boolean, default=True)
    mapping_confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 2)
    )  # 0-100% confidence
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Foreign keys
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tally_clients.id"), nullable=False
    )

    # Relationships
    client = relationship("TallyClient", back_populates="schedule_iii_mappings")

    def __repr__(self) -> str:
        return f"<ScheduleIIIMapping {self.ledger_name} → {self.schedule_iii_line}>"


class GeneratedReport(Base, TimestampMixin):
    """Tracks generated report files (Excel/PDF) for download."""

    __tablename__ = "generated_reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    report_type: Mapped[ReportType] = mapped_column(
        Enum(ReportType), nullable=False
    )
    report_format: Mapped[ReportFormat] = mapped_column(
        Enum(ReportFormat), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Foreign keys
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tally_clients.id"), nullable=False
    )

    # Relationships
    client = relationship("TallyClient", back_populates="generated_reports")

    def __repr__(self) -> str:
        return f"<GeneratedReport {self.file_name}>"
