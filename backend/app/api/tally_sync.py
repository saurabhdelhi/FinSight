"""Tally Sync API — trigger sync, check status, view data."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, DBSession
from app.models.client import TallyClient
from app.models.tally import TallyLedger
from app.schemas.tally import (
    SyncJobResponse,
    SyncTriggerResponse,
    TallyLedgerResponse,
    TrialBalanceEntry,
    TrialBalanceResponse,
)
from app.services.tally_sync_service import TallySyncService

router = APIRouter(prefix="/api/clients/{client_id}", tags=["Tally Sync"])


async def _verify_client(client_id: str, user: CurrentUser, db: DBSession) -> TallyClient:
    result = await db.execute(
        select(TallyClient).where(
            TallyClient.id == client_id,
            TallyClient.org_id == user.org_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("/sync", response_model=SyncTriggerResponse)
async def trigger_sync(client_id: str, current_user: CurrentUser, db: DBSession):
    """Trigger a full Tally data sync."""
    await _verify_client(client_id, current_user, db)
    sync_service = TallySyncService(db)
    sync_job = await sync_service.sync_client(client_id)
    return SyncTriggerResponse(
        job_id=sync_job.id,
        status=sync_job.status.value,
        message=f"Sync completed: {sync_job.ledgers_synced} ledgers, {sync_job.vouchers_synced} vouchers",
    )


@router.get("/sync/status", response_model=SyncJobResponse | None)
async def sync_status(client_id: str, current_user: CurrentUser, db: DBSession):
    """Get the latest sync job status."""
    await _verify_client(client_id, current_user, db)
    sync_service = TallySyncService(db)
    job = await sync_service.get_sync_status(client_id)
    if not job:
        return None
    return SyncJobResponse.model_validate(job)


@router.get("/sync/history", response_model=list[SyncJobResponse])
async def sync_history(client_id: str, current_user: CurrentUser, db: DBSession):
    """Get sync job history."""
    await _verify_client(client_id, current_user, db)
    sync_service = TallySyncService(db)
    jobs = await sync_service.get_sync_history(client_id)
    return [SyncJobResponse.model_validate(j) for j in jobs]


@router.get("/ledgers", response_model=list[TallyLedgerResponse])
async def list_ledgers(client_id: str, current_user: CurrentUser, db: DBSession):
    """List all synced ledgers for a client."""
    await _verify_client(client_id, current_user, db)
    result = await db.execute(
        select(TallyLedger)
        .where(TallyLedger.client_id == client_id)
        .order_by(TallyLedger.parent, TallyLedger.name)
    )
    ledgers = result.scalars().all()
    return [TallyLedgerResponse.model_validate(l) for l in ledgers]


@router.get("/trial-balance", response_model=TrialBalanceResponse)
async def get_trial_balance(client_id: str, current_user: CurrentUser, db: DBSession):
    """Get the trial balance for a client."""
    client = await _verify_client(client_id, current_user, db)
    result = await db.execute(
        select(TallyLedger)
        .where(TallyLedger.client_id == client_id)
        .order_by(TallyLedger.parent, TallyLedger.name)
    )
    ledgers = result.scalars().all()

    if not ledgers:
        raise HTTPException(status_code=412, detail="No synced data. Run a sync first.")

    from datetime import datetime, timezone
    from decimal import Decimal

    entries = [
        TrialBalanceEntry(
            ledger_name=l.name,
            group=l.parent,
            opening_balance=l.opening_balance,
            debit=l.debit_total,
            credit=l.credit_total,
            closing_balance=l.closing_balance,
        )
        for l in ledgers
    ]

    return TrialBalanceResponse(
        client_id=client_id,
        financial_year=client.financial_year,
        entries=entries,
        total_debit=sum(l.debit_total for l in ledgers),
        total_credit=sum(l.credit_total for l in ledgers),
        as_of=datetime.now(timezone.utc),
    )
