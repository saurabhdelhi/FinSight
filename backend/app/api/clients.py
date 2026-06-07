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

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    await db.flush()
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(client_id: str, current_user: CurrentUser, db: DBSession):
    """Delete a Tally client and all associated data."""
    result = await db.execute(
        select(TallyClient).where(
            TallyClient.id == client_id,
            TallyClient.org_id == current_user.org_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    await db.delete(client)
    await db.flush()


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
