"""Tally data models — Group, Ledger, Voucher, VoucherEntry."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, generate_uuid


class TallyGroup(Base, TimestampMixin):
    """A Tally group (account category) synced from Tally Prime."""

    __tablename__ = "tally_groups"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent: Mapped[str | None] = mapped_column(String(255))
    tally_guid: Mapped[str | None] = mapped_column(String(255))
    alter_id: Mapped[int | None] = mapped_column(Integer)
    is_revenue: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deemedpositive: Mapped[bool] = mapped_column(Boolean, default=False)
    affects_gross_profit: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_position: Mapped[int] = mapped_column(Integer, default=0)

    # Foreign keys
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tally_clients.id"), nullable=False
    )

    # Relationships
    client = relationship("TallyClient", back_populates="groups")

    def __repr__(self) -> str:
        return f"<TallyGroup {self.name}>"


class TallyLedger(Base, TimestampMixin):
    """A Tally ledger (account) synced from Tally Prime."""

    __tablename__ = "tally_ledgers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    parent: Mapped[str] = mapped_column(String(255), nullable=False)
    tally_guid: Mapped[str | None] = mapped_column(String(255))
    alter_id: Mapped[int | None] = mapped_column(Integer)
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00")
    )
    closing_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00")
    )
    debit_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00")
    )
    credit_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00")
    )
    # Additional master fields
    address: Mapped[str | None] = mapped_column(Text)
    gstin: Mapped[str | None] = mapped_column(String(15))
    pan: Mapped[str | None] = mapped_column(String(10))
    is_bill_wise: Mapped[bool] = mapped_column(Boolean, default=False)
    is_cost_centres_on: Mapped[bool] = mapped_column(Boolean, default=False)

    # Foreign keys
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tally_clients.id"), nullable=False
    )

    # Relationships
    client = relationship("TallyClient", back_populates="ledgers")
    voucher_entries: Mapped[list["TallyVoucherEntry"]] = relationship(
        "TallyVoucherEntry", back_populates="ledger", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TallyLedger {self.name} bal={self.closing_balance}>"


class TallyVoucher(Base, TimestampMixin):
    """A Tally voucher (transaction) synced from Tally Prime."""

    __tablename__ = "tally_vouchers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    tally_guid: Mapped[str | None] = mapped_column(String(255))
    alter_id: Mapped[int | None] = mapped_column(Integer)
    voucher_type: Mapped[str] = mapped_column(String(100), nullable=False)
    voucher_number: Mapped[str | None] = mapped_column(String(100))
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    party_name: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    narration: Mapped[str | None] = mapped_column(Text)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)

    # Foreign keys
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tally_clients.id"), nullable=False
    )

    # Relationships
    client = relationship("TallyClient", back_populates="vouchers")
    entries: Mapped[list["TallyVoucherEntry"]] = relationship(
        "TallyVoucherEntry", back_populates="voucher", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TallyVoucher {self.voucher_type} #{self.voucher_number} {self.date}>"


class TallyVoucherEntry(Base):
    """An individual ledger entry within a voucher (Dr/Cr line)."""

    __tablename__ = "tally_voucher_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    ledger_name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    is_debit: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Foreign keys
    voucher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tally_vouchers.id"), nullable=False
    )
    ledger_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tally_ledgers.id")
    )

    # Relationships
    voucher: Mapped["TallyVoucher"] = relationship(
        "TallyVoucher", back_populates="entries"
    )
    ledger: Mapped["TallyLedger | None"] = relationship(
        "TallyLedger", back_populates="voucher_entries"
    )
