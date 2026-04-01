from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.quote import Quote, QuoteStatus
from app.models.activity_log import ActivityLog, ActivityEventType
from app.models.user import User
from app.schemas.quote_schema import QuoteOut, PublicQuoteRespond
from app.services.email_service import send_client_response_notification
from app.config import get_settings

router = APIRouter(prefix="/public", tags=["Public Quote"])
settings = get_settings()

ACTION_TO_STATUS = {
    "approved": QuoteStatus.approved,
    "rejected": QuoteStatus.rejected,
    "changes_requested": QuoteStatus.changes_requested,
}

ACTION_TO_EVENT = {
    "approved": ActivityEventType.client_approved,
    "rejected": ActivityEventType.client_rejected,
    "changes_requested": ActivityEventType.client_changes_requested,
}


async def _get_by_token(token: str, db: AsyncSession) -> Quote:
    result = await db.execute(
        select(Quote)
        .options(
            selectinload(Quote.client),
            selectinload(Quote.items),
            selectinload(Quote.activity_logs),
        )
        .where(Quote.public_token == token)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found or link is invalid.")
    return quote


@router.get("/quote/{token}", response_model=QuoteOut, summary="Client views quote (no login)")
async def view_public_quote(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    quote = await _get_by_token(token, db)

    already_opened = any(
        log.event_type == ActivityEventType.client_opened
        for log in quote.activity_logs
    )
    if not already_opened:
        client_ip = request.client.host if request.client else "unknown"
        db.add(ActivityLog(
            quote_id=quote.id,
            event_type=ActivityEventType.client_opened,
            description=f"Client opened quote from IP {client_ip}",
            performed_by=None,
        ))
        await db.commit()

    return quote


@router.post("/quote/{token}/respond", response_model=dict, summary="Client approves / rejects / requests changes")
async def respond_to_quote(
    token: str,
    payload: PublicQuoteRespond,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if payload.action not in ACTION_TO_STATUS:
        raise HTTPException(
            status_code=400,
            detail="Invalid action. Use: approved, rejected, or changes_requested.",
        )

    quote = await _get_by_token(token, db)
    quote.status = ACTION_TO_STATUS[payload.action]
    quote.client_comment = payload.comment

    db.add(ActivityLog(
        quote_id=quote.id,
        event_type=ACTION_TO_EVENT[payload.action],
        description=f"Client {payload.action}: {payload.comment or ''}",
        performed_by=None,
    ))
    await db.commit()

    owner_result = await db.execute(select(User).where(User.id == quote.created_by))
    owner = owner_result.scalar_one_or_none()
    if owner:
        public_url = f"{settings.frontend_url}/public/quote/{token}"
        background_tasks.add_task(
            send_client_response_notification,
            owner.email,
            owner.full_name,
            quote.quote_number,
            payload.action,
            payload.comment or "",
            public_url,
        )

    return {"message": "Response recorded.", "status": quote.status.value}
