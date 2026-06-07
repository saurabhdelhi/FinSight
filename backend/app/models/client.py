"""Tally Client and Sync Job models."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, generate_uuid


class SyncStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TallyClient(Base, TimestampMixin):
    """
    A Tally Prime company/client managed by the CA firm.
    Each client has its own Tally connection details and synced data.
    """

    __tablename__ = "tally_clients"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tally_host: Mapped[str] = mapped_column(
        String(255), default="localhost", nullable=False
    )
    tally_port: Mapped[int] = mapped_column(Integer, default=9000, nullable=False)
    financial_year: Mapped[str] = mapped_column(
        String(9), nullable=False
    )  # e.g., "2025-2026"
    company_number: Mapped[str | None] = mapped_column(String(50))  # CIN
    gstin: Mapped[str | None] = mapped_column(String(15))
    pan: Mapped[str | None] = mapped_column(String(10))
    notes: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Foreign keys
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization", back_populates="clients"
    )
    sync_jobs: Mapped[list["SyncJob"]] = relationship(
        "SyncJob", back_populates="client", cascade="all, delete-orphan",
        order_by="SyncJob.created_at.desc()"
    )
    ledgers: Mapped[list] = relationship(
        "TallyLedger", back_populates="client", cascade="all, delete-orphan"
    )
    groups: Mapped[list] = relationship(
        "TallyGroup", back_populates="client", cascade="all, delete-orphan"
    )
    vouchers: Mapped[list] = relationship(
        "TallyVoucher", back_populates="client", cascade="all, delete-orphan"
    )
    audit_runs: Mapped[list] = relationship(
        "AuditRun", back_populates="client", cascade="all, delete-orphan"
    )
    schedule_iii_mappings: Mapped[list] = relationship(
        "ScheduleIIIMapping", back_populates="client", cascade="all, delete-orphan"
    )
    generated_reports: Mapped[list] = relationship(
        "GeneratedReport", back_populates="client", cascade="all, delete-orphan"
    )

    @property
    def tally_url(self) -> str:
        return f"http://{self.tally_host}:{self.tally_port}"

    def __repr__(self) -> str:
        return f"<TallyClient {self.company_name}>"


class SyncJob(Base, TimestampMixin):
    """Tracks each Tally data sync job for a client."""

    __tablename__ = "sync_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus), default=SyncStatus.PENDING, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    groups_synced: Mapped[int] = mapped_column(Integer, default=0)
    ledgers_synced: Mapped[int] = mapped_column(Integer, default=0)
    vouchers_synced: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Foreign keys
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tally_clients.id"), nullable=False
    )

    # Relationships
    client: Mapped["TallyClient"] = relationship(
        "TallyClient", back_populates="sync_jobs"
    )

    def __repr__(self) -> str:
        return f"<SyncJob {self.id[:8]} status={self.status}>"
