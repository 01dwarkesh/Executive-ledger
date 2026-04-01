import io
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd

from app.database import get_db
from app.models.client import Client
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.activity_log import ActivityLog, ActivityEventType
from app.models.user import User
from app.schemas.quote_schema import ImportResult
from app.dependencies.auth_dependencies import get_current_user
from app.utils.number_utils import generate_quote_number, calculate_final_price

router = APIRouter(prefix="/import", tags=["Import"])

REQUIRED_COLS = {"client_name", "email", "product_name", "quantity", "unit_price"}


@router.post("/quotes", response_model=ImportResult)
async def import_quotes(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk import quotes from CSV or Excel.

    Required columns: client_name, email, product_name, quantity, unit_price
    Optional columns: discount, size, color, lead_time, notes, validity_date, currency

    Creates clients automatically if not found (matched by email).
    Each row becomes one quote with one line item.
    """
    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .csv, .xlsx, or .xls files are accepted.")

    contents = await file.read()
    errors: List[str] = []
    created = 0

    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(sorted(missing))}",
        )

    for idx, row in df.iterrows():
        row_num = int(idx) + 2
        try:
            client_name = str(row.get("client_name", "")).strip()
            email = str(row.get("email", "")).strip()
            product_name = str(row.get("product_name", "")).strip()

            if not client_name or not email or not product_name:
                errors.append(f"Row {row_num}: client_name, email, and product_name are required.")
                continue

            try:
                quantity = int(row.get("quantity", 1))
                unit_price = float(row.get("unit_price", 0))
            except (ValueError, TypeError):
                errors.append(f"Row {row_num}: quantity and unit_price must be numbers.")
                continue

            discount = float(row.get("discount", 0) or 0)
            size = str(row.get("size", "") or "").strip() or None
            color = str(row.get("color", "") or "").strip() or None
            lead_time = str(row.get("lead_time", "") or "").strip() or None
            notes = str(row.get("notes", "") or "").strip() or None
            currency = str(row.get("currency", "USD") or "USD").strip()

            # Find or create client
            client_result = await db.execute(
                select(Client).where(Client.email == email, Client.created_by == current_user.id)
            )
            client = client_result.scalar_one_or_none()
            if not client:
                client = Client(
                    company_name=client_name,
                    contact_name=client_name,
                    email=email,
                    created_by=current_user.id,
                )
                db.add(client)
                await db.flush()

            quote_number = await generate_quote_number(db)
            quote = Quote(
                quote_number=quote_number,
                client_id=client.id,
                created_by=current_user.id,
                notes=notes,
                currency=currency,
            )
            db.add(quote)
            await db.flush()

            final_price = calculate_final_price(quantity, unit_price, discount)
            db.add(QuoteItem(
                quote_id=quote.id,
                product_name=product_name,
                quantity=quantity,
                unit_price=unit_price,
                discount_pct=discount,
                final_price=final_price,
                size_capacity=size,
                color=color,
                lead_time=lead_time,
            ))

            db.add(ActivityLog(
                quote_id=quote.id,
                event_type=ActivityEventType.quote_created,
                description=f"Quote created via CSV import by {current_user.full_name}",
                performed_by=current_user.id,
            ))

            await db.flush()
            created += 1

        except Exception as e:
            errors.append(f"Row {row_num}: Unexpected error — {str(e)}")

    if created > 0:
        await db.commit()

    return ImportResult(created=created, errors=errors)