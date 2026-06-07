"""
Tally sync orchestration service.

Manages the full data sync lifecycle: connect → fetch → parse → persist.
Supports full sync and delta sync (via AlterID tracking).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, date
from decimal import Decimal

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SyncInProgressError, NoSyncDataError
from app.models.client import SyncJob, SyncStatus, TallyClient
from app.models.tally import TallyGroup, TallyLedger, TallyVoucher, TallyVoucherEntry
from app.services.tally_connector import TallyConnector
from app.services.tally_parser import TallyParser

logger = logging.getLogger(__name__)


def _fy_dates(financial_year: str) -> tuple[str, str]:
    """
    Convert financial year string (e.g. '2025-2026') to Tally date
    format (YYYYMMDD) for start and end.
    Indian FY runs April 1 to March 31.
    """
    start_year, end_year = financial_year.split("-")
    from_date = f"{start_year}0401"  # April 1
    to_date = f"{end_year}0331"  # March 31
    return from_date, to_date


class TallySyncService:
    """Orchestrates Tally data synchronization for a client."""

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

    async def _check_no_running_sync(self, client_id: str) -> None:
        """Ensure no other sync is currently running for this client."""
        result = await self.db.execute(
            select(SyncJob).where(
                SyncJob.client_id == client_id,
                SyncJob.status == SyncStatus.RUNNING,
            )
        )
        if result.scalar_one_or_none():
            raise SyncInProgressError(client_id)

    async def test_connection(self, client_id: str) -> dict:
        """Test connectivity to the Tally instance for a client."""
        client = await self._get_client(client_id)
        connector = TallyConnector(
            host=client.tally_host,
            port=client.tally_port,
        )
        response_xml = await connector.test_connection()
        companies = TallyParser.parse_company_info(response_xml)

        return {
            "success": True,
            "message": f"Connected to Tally at {client.tally_url}",
            "company_name": companies[0].name if companies else None,
        }

    async def sync_client(self, client_id: str) -> SyncJob:
        """
        Execute a full sync for a Tally client.

        Flow:
        1. Create SyncJob → RUNNING
        2. Fetch & persist groups
        3. Fetch & persist ledgers
        4. Fetch & persist vouchers (for the financial year)
        5. Update SyncJob → COMPLETED
        """
        client = await self._get_client(client_id)
        await self._check_no_running_sync(client_id)

        # Create sync job
        sync_job = SyncJob(
            client_id=client_id,
            status=SyncStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(sync_job)
        await self.db.flush()

        connector = TallyConnector(
            host=client.tally_host,
            port=client.tally_port,
        )

        try:
            # ── Step 1: Sync Groups ──────────────────────────────────────
            logger.info(f"[Sync {sync_job.id[:8]}] Fetching groups...")
            groups_xml = await connector.fetch_groups()
            parsed_groups = TallyParser.parse_groups(groups_xml)

            # Clear existing groups and insert fresh
            await self.db.execute(
                delete(TallyGroup).where(TallyGroup.client_id == client_id)
            )
            for pg in parsed_groups:
                group = TallyGroup(
                    client_id=client_id,
                    name=pg.name,
                    parent=pg.parent,
                    tally_guid=pg.guid,
                    alter_id=pg.alter_id,
                    is_revenue=pg.is_revenue,
                    is_deemedpositive=pg.is_deemedpositive,
                    affects_gross_profit=pg.affects_gross_profit,
                    sort_position=pg.sort_position,
                )
                self.db.add(group)

            sync_job.groups_synced = len(parsed_groups)
            await self.db.flush()
            logger.info(f"[Sync {sync_job.id[:8]}] Synced {len(parsed_groups)} groups")

            # ── Step 2: Sync Ledgers ─────────────────────────────────────
            logger.info(f"[Sync {sync_job.id[:8]}] Fetching ledgers...")
            ledgers_xml = await connector.fetch_ledgers()
            parsed_ledgers = TallyParser.parse_ledgers(ledgers_xml)

            # Clear existing ledgers (cascade will remove voucher_entries FKs)
            await self.db.execute(
                delete(TallyVoucherEntry).where(
                    TallyVoucherEntry.ledger_id.in_(
                        select(TallyLedger.id).where(
                            TallyLedger.client_id == client_id
                        )
                    )
                )
            )
            await self.db.execute(
                delete(TallyLedger).where(TallyLedger.client_id == client_id)
            )

            ledger_name_to_id: dict[str, str] = {}
            for pl in parsed_ledgers:
                ledger = TallyLedger(
                    client_id=client_id,
                    name=pl.name,
                    parent=pl.parent,
                    tally_guid=pl.guid,
                    alter_id=pl.alter_id,
                    opening_balance=pl.opening_balance,
                    closing_balance=pl.closing_balance,
                    address=pl.address,
                    gstin=pl.gstin,
                    pan=pl.pan,
                    is_bill_wise=pl.is_bill_wise,
                    is_cost_centres_on=pl.is_cost_centres_on,
                )
                self.db.add(ledger)
                await self.db.flush()
                ledger_name_to_id[pl.name] = ledger.id

            sync_job.ledgers_synced = len(parsed_ledgers)
            await self.db.flush()
            logger.info(
                f"[Sync {sync_job.id[:8]}] Synced {len(parsed_ledgers)} ledgers"
            )

            # ── Step 3: Sync Vouchers ────────────────────────────────────
            logger.info(f"[Sync {sync_job.id[:8]}] Fetching vouchers...")
            from_date, to_date = _fy_dates(client.financial_year)
            vouchers_xml = await connector.fetch_vouchers(from_date, to_date)
            parsed_vouchers = TallyParser.parse_vouchers(vouchers_xml)

            # Clear existing vouchers
            await self.db.execute(
                delete(TallyVoucher).where(TallyVoucher.client_id == client_id)
            )

            for pv in parsed_vouchers:
                # Parse date from YYYYMMDD
                try:
                    vch_date = date(
                        int(pv.date[:4]), int(pv.date[4:6]), int(pv.date[6:8])
                    )
                except (ValueError, IndexError):
                    vch_date = date.today()

                voucher = TallyVoucher(
                    client_id=client_id,
                    tally_guid=pv.guid,
                    alter_id=pv.alter_id,
                    voucher_type=pv.voucher_type,
                    voucher_number=pv.voucher_number,
                    date=vch_date,
                    party_name=pv.party_name,
                    amount=pv.amount,
                    narration=pv.narration,
                    is_cancelled=pv.is_cancelled,
                    is_optional=pv.is_optional,
                )
                self.db.add(voucher)
                await self.db.flush()

                # Add ledger entries
                for pe in pv.entries:
                    entry = TallyVoucherEntry(
                        voucher_id=voucher.id,
                        ledger_name=pe.ledger_name,
                        amount=pe.amount,
                        is_debit=pe.is_debit,
                        ledger_id=ledger_name_to_id.get(pe.ledger_name),
                    )
                    self.db.add(entry)

            sync_job.vouchers_synced = len(parsed_vouchers)
            await self.db.flush()
            logger.info(
                f"[Sync {sync_job.id[:8]}] Synced {len(parsed_vouchers)} vouchers"
            )

            # ── Finalize ─────────────────────────────────────────────────
            sync_job.status = SyncStatus.COMPLETED
            sync_job.completed_at = datetime.now(timezone.utc)
            client.last_synced_at = datetime.now(timezone.utc)
            await self.db.flush()

            logger.info(
                f"[Sync {sync_job.id[:8]}] ✓ Sync completed: "
                f"{sync_job.groups_synced} groups, "
                f"{sync_job.ledgers_synced} ledgers, "
                f"{sync_job.vouchers_synced} vouchers"
            )
            return sync_job

        except Exception as e:
            sync_job.status = SyncStatus.FAILED
            sync_job.completed_at = datetime.now(timezone.utc)
            sync_job.error_message = str(e)
            await self.db.flush()
            logger.error(f"[Sync {sync_job.id[:8]}] ✗ Sync failed: {e}")
            raise

    async def get_sync_status(self, client_id: str) -> SyncJob | None:
        """Get the most recent sync job for a client."""
        result = await self.db.execute(
            select(SyncJob)
            .where(SyncJob.client_id == client_id)
            .order_by(SyncJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_sync_history(
        self, client_id: str, limit: int = 20
    ) -> list[SyncJob]:
        """Get sync job history for a client."""
        result = await self.db.execute(
            select(SyncJob)
            .where(SyncJob.client_id == client_id)
            .order_by(SyncJob.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
