from typing import List, Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from io import BytesIO

from app.database import get_db
from app.models.quote import Quote, QuoteStatus
from app.models.client import Client
from app.models.activity_log import ActivityLog, ActivityEventType
from app.models.user import User
from app.schemas.quote_schema import (
    QuoteCreate, QuoteUpdate, QuoteOut, QuoteListOut,
    SendQuoteRequest, DashboardStats,
)
from app.schemas.activity_schema import ActivityLogOut
from app.dependencies.auth_dependencies import get_current_user, apply_ownership_filter
from app.services import quote_service
from app.services.email_service import send_quote_link
from app.services.pdf_service import generate_pdf
from app.utils.number_utils import generate_quote_number
from app.config import get_settings

router = APIRouter(prefix="/quotes", tags=["Quotes"])
settings = get_settings()


async def _get_own_quote(quote_id: str, current_user: User, db: AsyncSession) -> Quote:
    q = apply_ownership_filter(select(Quote).where(Quote.id == quote_id), Quote, current_user)
    quote = (await db.execute(q)).scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found.")
    return quote


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stats = await quote_service.get_dashboard_stats(current_user, db)
    return DashboardStats(**stats)


@router.get("/", response_model=List[QuoteListOut])
async def list_quotes(
    status: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Quote).options(selectinload(Quote.client))
    q = apply_ownership_filter(q, Quote, current_user)
    if status:
        q = q.where(Quote.status == status)
    if client_id:
        q = q.where(Quote.client_id == client_id)
    if search:
        q = q.where(Quote.quote_number.ilike(f"%{search}%"))
    q = q.order_by(Quote.updated_at.desc()).offset(skip).limit(limit)
    return (await db.execute(q)).scalars().all()


@router.post("/", response_model=QuoteOut, status_code=201)
async def create_quote(
    payload: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client_q = apply_ownership_filter(
        select(Client).where(Client.id == payload.client_id), Client, current_user
    )
    if not (await db.execute(client_q)).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found.")

    quote_number = await generate_quote_number(db)
    quote = Quote(quote_number=quote_number, created_by=current_user.id, **payload.model_dump())
    db.add(quote)
    await db.flush()

    db.add(quote_service.make_log(
        quote.id, ActivityEventType.quote_created,
        f"Quote {quote_number} created", current_user.id,
    ))
    await db.commit()
    return await quote_service.get_quote_with_relations(str(quote.id), db)


@router.get("/{quote_id}", response_model=QuoteOut)
async def get_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_own_quote(quote_id, current_user, db)
    return await quote_service.get_quote_with_relations(quote_id, db)


@router.put("/{quote_id}", response_model=QuoteOut)
async def update_quote(
    quote_id: str,
    payload: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quote = await _get_own_quote(quote_id, current_user, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(quote, field, value)
    db.add(quote_service.make_log(
        quote.id, ActivityEventType.updated,
        "Quote metadata updated", current_user.id,
    ))
    await db.commit()
    return await quote_service.get_quote_with_relations(quote_id, db)


@router.delete("/{quote_id}", response_model=dict)
async def delete_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quote = await _get_own_quote(quote_id, current_user, db)
    await db.delete(quote)
    await db.commit()
    return {"message": "Quote deleted."}


@router.post("/{quote_id}/new-version", response_model=QuoteOut)
async def new_version(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_own_quote(quote_id, current_user, db)
    source = await quote_service.get_quote_with_relations(quote_id, db)
    return await quote_service.create_new_version(source, current_user, db)


@router.get("/{quote_id}/versions", response_model=List[QuoteListOut])
async def get_versions(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = await _get_own_quote(quote_id, current_user, db)
    parent_id = source.parent_quote_id or source.id
    q = (
        select(Quote)
        .options(selectinload(Quote.client))
        .where((Quote.id == parent_id) | (Quote.parent_quote_id == parent_id))
        .order_by(Quote.version)
    )
    return (await db.execute(q)).scalars().all()


@router.post("/{quote_id}/send-email", response_model=dict)
async def send_quote_email(
    quote_id: str,
    payload: SendQuoteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quote = await quote_service.get_quote_with_relations(quote_id, db)
    await _get_own_quote(quote_id, current_user, db)

    quote.status = QuoteStatus.sent
    db.add(quote_service.make_log(
        quote.id, ActivityEventType.quote_sent,
        "Quote sent to client via email", current_user.id,
    ))
    await db.commit()

    public_url = f"{settings.frontend_url}/public/quote/{quote.public_token}"
    background_tasks.add_task(
        send_quote_link,
        quote.client.email,
        quote.client.contact_name,
        quote.quote_number,
        public_url,
    )
    return {"message": "Quote sent.", "public_token": quote.public_token}


@router.get("/{quote_id}/export-pdf")
async def download_pdf(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_own_quote(quote_id, current_user, db)
    quote = await quote_service.get_quote_with_relations(quote_id, db)
    pdf_bytes = generate_pdf(quote)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote.quote_number}.pdf"'},
    )


@router.get("/{quote_id}/activity", response_model=List[ActivityLogOut])
async def get_activity(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_own_quote(quote_id, current_user, db)
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.quote_id == quote_id)
        .order_by(ActivityLog.created_at.desc())
    )
    return [ActivityLogOut.model_validate(r) for r in result.scalars().all()]
