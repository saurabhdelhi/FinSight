"""Tally Client CRUD API."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, DBSession
from app.models.client import TallyClient
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    ConnectionTestResponse,
)
from app.services.tally_sync_service import TallySyncService

router = APIRouter(prefix="/api/clients", tags=["Clients"])


@router.get("", response_model=ClientListResponse)
async def list_clients(current_user: CurrentUser, db: DBSession):
    """List all Tally clients for the user's organization."""
    result = await db.execute(
        select(TallyClient)
        .where(TallyClient.org_id == current_user.org_id)
        .order_by(TallyClient.company_name)
    )
    clients = list(result.scalars().all())
    return ClientListResponse(
        clients=[ClientResponse.model_validate(c) for c in clients],
        total=len(clients),
    )


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate, current_user: CurrentUser, db: DBSession
):
    """Add a new Tally client."""
    # Check for duplicate client (same name and financial year in the same organization)
    stmt = select(TallyClient).where(
        TallyClient.company_name == payload.company_name,
        TallyClient.financial_year == payload.financial_year,
        TallyClient.org_id == current_user.org_id,
    )
    result = await db.execute(stmt)
    existing_client = result.scalar_one_or_none()
    if existing_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A client with name '{payload.company_name}' and financial year '{payload.financial_year}' already exists.",
        )

    client = TallyClient(
        org_id=current_user.org_id,
        company_name=payload.company_name,
        tally_host=payload.tally_host,
        tally_port=payload.tally_port,
        financial_year=payload.financial_year,
        company_number=payload.company_number,
        gstin=payload.gstin,
        pan=payload.pan,
        notes=payload.notes,
    )
    db.add(client)
    await db.flush()
    return ClientResponse.model_validate(client)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: str, current_user: CurrentUser, db: DBSession):
    """Get a specific Tally client."""
    result = await db.execute(
        select(TallyClient).where(
            TallyClient.id == client_id,
            TallyClient.org_id == current_user.org_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientResponse.model_validate(client)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str, payload: ClientUpdate, current_user: CurrentUser, db: DBSession
):
    """Update a Tally client."""
    result = await db.execute(
        select(TallyClient).where(
            TallyClient.id == client_id,
            TallyClient.org_id == current_user.org_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # If name or financial year is changing, check for duplicates
    new_name = payload.company_name if payload.company_name is not None else client.company_name
    new_fy = payload.financial_year if payload.financial_year is not None else client.financial_year
    if new_name != client.company_name or new_fy != client.financial_year:
        stmt = select(TallyClient).where(
            TallyClient.company_name == new_name,
            TallyClient.financial_year == new_fy,
            TallyClient.org_id == current_user.org_id,
            TallyClient.id != client_id,
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A client with name '{new_name}' and financial year '{new_fy}' already exists.",
            )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    await db.flush()
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(client_id: str, current_user: CurrentUser, db: DBSession):
    """Delete a Tally client and all associated data.

    Executes direct SQL DELETE statements in the correct dependency order
    to bypass ORM lazy-loading limits and avoid database constraint violations.
    """
    import logging
    from sqlalchemy import delete
    from app.models.tally import TallyGroup, TallyLedger, TallyVoucher, TallyVoucherEntry
    from app.models.audit import AuditRun, AuditFinding
    from app.models.report import GeneratedReport, ScheduleIIIMapping
    from app.models.client import SyncJob

    logger = logging.getLogger(__name__)

    # Query client name and existence first
    result = await db.execute(
        select(TallyClient.company_name).where(
            TallyClient.id == client_id,
            TallyClient.org_id == current_user.org_id,
        )
    )
    company_name = result.scalar_one_or_none()
    if not company_name:
        raise HTTPException(status_code=404, detail="Client not found")

    try:
        # 1. Delete audit findings (fk references audit_runs.id)
        audit_run_ids = select(AuditRun.id).where(AuditRun.client_id == client_id)
        await db.execute(
            delete(AuditFinding).where(AuditFinding.audit_run_id.in_(audit_run_ids))
        )

        # 2. Delete audit runs
        await db.execute(
            delete(AuditRun).where(AuditRun.client_id == client_id)
        )

        # 3. Delete voucher entries (fk references tally_vouchers.id)
        voucher_ids = select(TallyVoucher.id).where(TallyVoucher.client_id == client_id)
        await db.execute(
            delete(TallyVoucherEntry).where(TallyVoucherEntry.voucher_id.in_(voucher_ids))
        )

        # 4. Delete vouchers
        await db.execute(
            delete(TallyVoucher).where(TallyVoucher.client_id == client_id)
        )

        # 5. Delete ledgers
        await db.execute(
            delete(TallyLedger).where(TallyLedger.client_id == client_id)
        )

        # 6. Delete groups
        await db.execute(
            delete(TallyGroup).where(TallyGroup.client_id == client_id)
        )

        # 7. Delete sync jobs
        await db.execute(
            delete(SyncJob).where(SyncJob.client_id == client_id)
        )

        # 8. Delete Schedule III mappings
        await db.execute(
            delete(ScheduleIIIMapping).where(ScheduleIIIMapping.client_id == client_id)
        )

        # 9. Delete generated reports
        await db.execute(
            delete(GeneratedReport).where(GeneratedReport.client_id == client_id)
        )

        # 10. Finally, delete the client itself
        await db.execute(
            delete(TallyClient).where(TallyClient.id == client_id)
        )

        await db.flush()
        logger.info("Successfully deleted client %s (%s) and all associated data", client_id, company_name)
    except Exception as e:
        logger.error("Failed to delete client %s: %s", client_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete client: {str(e)}",
        )


@router.post("/{client_id}/test-connection", response_model=ConnectionTestResponse)
async def test_connection(client_id: str, current_user: CurrentUser, db: DBSession):
    """Test connectivity to the Tally Prime instance."""
    result = await db.execute(
        select(TallyClient).where(
            TallyClient.id == client_id,
            TallyClient.org_id == current_user.org_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    try:
        sync_service = TallySyncService(db)
        response = await sync_service.test_connection(client_id)
        return ConnectionTestResponse(**response)
    except Exception as e:
        return ConnectionTestResponse(
            success=False,
            message=str(e),
        )
