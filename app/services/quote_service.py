from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.quote import Quote, QuoteStatus
from app.models.quote_item import QuoteItem
from app.models.activity_log import ActivityLog, ActivityEventType
from app.models.user import User
from app.utils.number_utils import generate_quote_number, calculate_final_price


def make_log(
    quote_id,
    event_type: ActivityEventType,
    description: str,
    performed_by=None,
) -> ActivityLog:
    return ActivityLog(
        quote_id=quote_id,
        event_type=event_type,
        description=description,
        performed_by=performed_by,
    )


async def get_quote_with_relations(quote_id: str, db: AsyncSession) -> Quote:
    result = await db.execute(
        select(Quote)
        .options(
            selectinload(Quote.client),
            selectinload(Quote.items),
            selectinload(Quote.activity_logs),
        )
        .where(Quote.id == quote_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found.")
    return quote


async def create_new_version(source_quote: Quote, current_user: User, db: AsyncSession) -> Quote:
    parent_id = source_quote.parent_quote_id or source_quote.id

    max_v_result = await db.execute(
        select(func.max(Quote.version)).where(
            (Quote.id == parent_id) | (Quote.parent_quote_id == parent_id)
        )
    )
    max_version = max_v_result.scalar_one() or source_quote.version

    new_number = await generate_quote_number(db)
    new_quote = Quote(
        quote_number=new_number,
        parent_quote_id=parent_id,
        version=max_version + 1,
        client_id=source_quote.client_id,
        created_by=current_user.id,
        validity_date=source_quote.validity_date,
        notes=source_quote.notes,
        internal_notes=source_quote.internal_notes,
        terms=source_quote.terms,
        currency=source_quote.currency,
        tax_pct=source_quote.tax_pct,
        adjustment=source_quote.adjustment,
        status=QuoteStatus.draft,
    )
    db.add(new_quote)
    await db.flush()

    for item in source_quote.items:
        db.add(QuoteItem(
            quote_id=new_quote.id,
            product_id=item.product_id,
            product_name=item.product_name,
            description=item.description,
            size_capacity=item.size_capacity,
            color=item.color,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_pct=item.discount_pct,
            final_price=item.final_price,
            lead_time=item.lead_time,
            logo_url=item.logo_url,
            mockup_url=item.mockup_url,
            logo_x=item.logo_x,
            logo_y=item.logo_y,
            logo_scale=item.logo_scale,
            sort_order=item.sort_order,
        ))

    db.add(make_log(
        new_quote.id,
        ActivityEventType.version_created,
        f"Version {new_quote.version} created from v{source_quote.version}",
        current_user.id,
    ))
    await db.commit()
    return await get_quote_with_relations(str(new_quote.id), db)


async def get_dashboard_stats(current_user: User, db: AsyncSession) -> dict:
    from app.dependencies.auth_dependencies import apply_ownership_filter

    async def count_status(status_val):
        q = select(func.count(Quote.id)).where(Quote.status == status_val)
        q = apply_ownership_filter(q, Quote, current_user)
        return (await db.execute(q)).scalar_one() or 0

    async def sum_value():
        q = select(func.sum(QuoteItem.final_price)).join(Quote, QuoteItem.quote_id == Quote.id)
        q = apply_ownership_filter(q, Quote, current_user)
        val = (await db.execute(q)).scalar_one()
        return Decimal(str(val)) if val else Decimal("0.00")

    active_statuses = [QuoteStatus.sent, QuoteStatus.approved, QuoteStatus.changes_requested]
    total_active = sum([await count_status(s) for s in active_statuses])

    return {
        "total_active": total_active,
        "pending_approval": await count_status(QuoteStatus.sent),
        "drafts": await count_status(QuoteStatus.draft),
        "approved": await count_status(QuoteStatus.approved),
        "rejected": await count_status(QuoteStatus.rejected),
        "total_value": await sum_value(),
    }
