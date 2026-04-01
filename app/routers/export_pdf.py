from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO

from app.database import get_db
from app.models.user import User
from app.dependencies.auth_dependencies import get_current_user, apply_ownership_filter
from app.services.quote_service import get_quote_with_relations
from app.services.pdf_service import generate_pdf
from sqlalchemy import select
from app.models.quote import Quote

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/pdf/{quote_id}", summary="Download quote as PDF (alias)")
async def export_pdf(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates and streams a PDF for the specified quote.
    Enforces ownership: sales users can only export their own quotes.
    """
    # ownership check
    q = apply_ownership_filter(
        select(Quote).where(Quote.id == quote_id), Quote, current_user
    )
    result = await db.execute(q)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Quote not found.")

    quote = await get_quote_with_relations(quote_id, db)
    pdf_bytes = generate_pdf(quote)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote.quote_number}-v{quote.version}.pdf"'},
    )