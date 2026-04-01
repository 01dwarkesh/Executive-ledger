import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.user import User
from app.schemas.quote_item_schema import (
    QuoteItemCreate, QuoteItemUpdate, QuoteItemOut,
    MockupSaveRequest, QuoteItemSummary,
)
from app.dependencies.auth_dependencies import get_current_user, apply_ownership_filter
from app.utils.number_utils import calculate_final_price
from app.utils.file_utils import save_upload, delete_file
from app.services.mockup_service import convert_to_grayscale, save_mockup_from_base64
from app.config import get_settings
from decimal import Decimal

router = APIRouter(prefix="/quotes/{quote_id}/items", tags=["Quote Items"])
settings = get_settings()


async def _assert_quote_owner(quote_id: str, current_user: User, db: AsyncSession) -> Quote:
    q = apply_ownership_filter(select(Quote).where(Quote.id == quote_id), Quote, current_user)
    quote = (await db.execute(q)).scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found.")
    return quote


async def _get_item(item_id: str, quote_id: str, db: AsyncSession) -> QuoteItem:
    result = await db.execute(
        select(QuoteItem).where(QuoteItem.id == item_id, QuoteItem.quote_id == quote_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found.")
    return item


@router.get("/", response_model=List[QuoteItemOut])
async def list_items(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_quote_owner(quote_id, current_user, db)
    result = await db.execute(
        select(QuoteItem).where(QuoteItem.quote_id == quote_id).order_by(QuoteItem.sort_order)
    )
    return result.scalars().all()


@router.get("/summary", response_model=QuoteItemSummary)
async def get_summary(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_quote_owner(quote_id, current_user, db)
    result = await db.execute(
        select(QuoteItem).where(QuoteItem.quote_id == quote_id)
    )
    items = result.scalars().all()

    subtotal = Decimal("0.00")
    total_discount_amount = Decimal("0.00")

    for item in items:
        qty = Decimal(str(item.quantity))
        unit = Decimal(str(item.unit_price))
        disc = Decimal(str(item.discount_pct))
        gross = qty * unit
        discount_amt = gross * disc / Decimal("100")
        subtotal += gross - discount_amt
        total_discount_amount += discount_amt

    return QuoteItemSummary(
        subtotal=subtotal,
        total_discount_amount=total_discount_amount,
        grand_total=subtotal,
        item_count=len(items),
    )


@router.post("/", response_model=QuoteItemOut, status_code=201)
async def add_item(
    quote_id: str,
    payload: QuoteItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_quote_owner(quote_id, current_user, db)
    final_price = calculate_final_price(payload.quantity, payload.unit_price, payload.discount_pct)
    item = QuoteItem(quote_id=quote_id, final_price=final_price, **payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/{item_id}", response_model=QuoteItemOut)
async def update_item(
    quote_id: str,
    item_id: str,
    payload: QuoteItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_quote_owner(quote_id, current_user, db)
    item = await _get_item(item_id, quote_id, db)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(item, field, value)

    item.final_price = calculate_final_price(item.quantity, item.unit_price, item.discount_pct)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", response_model=dict)
async def delete_item(
    quote_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_quote_owner(quote_id, current_user, db)
    item = await _get_item(item_id, quote_id, db)
    await db.delete(item)
    await db.commit()
    return {"message": "Item deleted."}


@router.post("/{item_id}/upload-logo", response_model=dict)
async def upload_logo(
    quote_id: str,
    item_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_quote_owner(quote_id, current_user, db)
    item = await _get_item(item_id, quote_id, db)

    if item.logo_url:
        delete_file(item.logo_url)

    url = await save_upload(file, f"logos/{quote_id}")
    item.logo_url = url
    await db.commit()
    return {"logo_url": url}


@router.post("/{item_id}/save-mockup", response_model=dict)
async def save_mockup(
    quote_id: str,
    item_id: str,
    payload: MockupSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accepts base64-encoded PNG from canvas export and saves as mockup image."""
    await _assert_quote_owner(quote_id, current_user, db)
    item = await _get_item(item_id, quote_id, db)

    url = save_mockup_from_base64(payload.mockup_image_base64, str(item_id), settings.upload_dir)
    item.mockup_url = url
    item.logo_x = payload.logo_x
    item.logo_y = payload.logo_y
    item.logo_scale = payload.logo_scale
    await db.commit()
    return {"mockup_url": url}


@router.post("/{item_id}/grayscale-logo", response_model=dict)
async def grayscale_logo(
    quote_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Converts the item's existing logo to grayscale in-place."""
    await _assert_quote_owner(quote_id, current_user, db)
    item = await _get_item(item_id, quote_id, db)

    if not item.logo_url:
        raise HTTPException(status_code=400, detail="No logo uploaded for this item.")

    rel = item.logo_url.replace("/uploads/", "", 1)
    full_path = os.path.join(settings.upload_dir, rel)

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Logo file not found on disk.")

    convert_to_grayscale(full_path)
    await db.commit()
    return {"logo_url": item.logo_url, "message": "Logo converted to grayscale."}
