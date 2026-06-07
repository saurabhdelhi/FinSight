"""Audit run and finding models."""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, generate_uuid


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuditRun(Base, TimestampMixin):
    """
    A single audit execution for a client.
    Each run executes all (or selected) audit rules and captures findings.
    """

    __tablename__ = "audit_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    rules_executed: Mapped[int] = mapped_column(Integer, default=0)
    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)
    info_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        String(20), default="completed", nullable=False
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    # Foreign keys
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tally_clients.id"), nullable=False
    )

    # Relationships
    client = relationship("TallyClient", back_populates="audit_runs")
    findings: Mapped[list["AuditFinding"]] = relationship(
        "AuditFinding", back_populates="audit_run", cascade="all, delete-orphan",
        order_by="AuditFinding.severity"
    )

    def __repr__(self) -> str:
        return f"<AuditRun {self.id[:8]} findings={self.total_findings} risk={self.risk_score:.1f}>"


class AuditFinding(Base, TimestampMixin):
    """An individual audit observation produced by a rule."""

    __tablename__ = "audit_findings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    rule_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g. "CASH_001"
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "Cash & Bank"
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ledger_name: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    recommendation: Mapped[str | None] = mapped_column(Text)
    reference: Mapped[str | None] = mapped_column(
        String(255)
    )  # e.g. "Section 269SS"
    details_json: Mapped[str | None] = mapped_column(
        Text
    )  # Additional structured data as JSON

    # Foreign keys
    audit_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audit_runs.id"), nullable=False
    )

    # Relationships
    audit_run: Mapped["AuditRun"] = relationship(
        "AuditRun", back_populates="findings"
    )

    def __repr__(self) -> str:
        return f"<AuditFinding {self.rule_id} severity={self.severity}>"
