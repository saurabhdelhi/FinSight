"""Schedule III API — mappings, balance sheet, P&L."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DBSession
from app.models.client import TallyClient
from app.schemas.report import (
    BalanceSheetResponse,
    MappingOverrideRequest,
    ProfitAndLossResponse,
    ScheduleIIIMappingResponse,
)
from app.services.schedule_iii_mapper import ScheduleIIIMapper

router = APIRouter(prefix="/api/clients/{client_id}/schedule-iii", tags=["Schedule III"])


async def _verify_client(client_id: str, user: CurrentUser, db: DBSession):
    result = await db.execute(
        select(TallyClient).where(
            TallyClient.id == client_id,
            TallyClient.org_id == user.org_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")


@router.get("/mappings", response_model=list[ScheduleIIIMappingResponse])
async def get_mappings(client_id: str, current_user: CurrentUser, db: DBSession):
    """Get all Schedule III mappings for a client."""
    await _verify_client(client_id, current_user, db)
    mapper = ScheduleIIIMapper(db)
    
    # Query existing mappings first to avoid unconditional recalculations and race conditions
    result = await db.execute(
        select(ScheduleIIIMapping)
        .where(ScheduleIIIMapping.client_id == client_id)
        .order_by(ScheduleIIIMapping.sort_order)
    )
    mappings = list(result.scalars().all())
    
    if not mappings:
        mappings = await mapper.map_client(client_id)
        
    return [ScheduleIIIMappingResponse.model_validate(m) for m in mappings]


@router.put("/mapping", response_model=ScheduleIIIMappingResponse)
async def override_mapping(
    client_id: str,
    payload: MappingOverrideRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Manually override a Schedule III mapping for a ledger."""
    await _verify_client(client_id, current_user, db)
    mapper = ScheduleIIIMapper(db)
    mapping = await mapper.override_mapping(
        client_id=client_id,
        ledger_name=payload.ledger_name,
        schedule_iii_line=payload.schedule_iii_line,
        category=payload.category,
        section=payload.section,
        sub_category=payload.sub_category,
    )
    return ScheduleIIIMappingResponse.model_validate(mapping)


@router.get("/balance-sheet")
async def get_balance_sheet(client_id: str, current_user: CurrentUser, db: DBSession):
    """Get the Balance Sheet in Schedule III format."""
    await _verify_client(client_id, current_user, db)
    mapper = ScheduleIIIMapper(db)
    return await mapper.get_balance_sheet(client_id)


@router.get("/profit-and-loss")
async def get_profit_and_loss(client_id: str, current_user: CurrentUser, db: DBSession):
    """Get the Statement of Profit & Loss in Schedule III format."""
    await _verify_client(client_id, current_user, db)
    mapper = ScheduleIIIMapper(db)
    return await mapper.get_profit_and_loss(client_id)
