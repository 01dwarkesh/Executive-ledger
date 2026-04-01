from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


async def generate_quote_number(db: AsyncSession) -> str:
    from app.models.quote import Quote

    year = datetime.utcnow().year
    prefix = f"Q-{year}-"
    result = await db.execute(
        select(Quote.quote_number)
        .where(Quote.quote_number.like(f"{prefix}%"))
        .order_by(Quote.quote_number.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    if last:
        try:
            last_num = int(last.split("-")[-1])
        except (ValueError, IndexError):
            last_num = 0
    else:
        last_num = 0
    return f"{prefix}{str(last_num + 1).zfill(3)}"


def calculate_final_price(quantity: int, unit_price: Decimal, discount_pct: Decimal) -> Decimal:
    unit = Decimal(str(unit_price))
    disc = Decimal(str(discount_pct))
    qty = Decimal(str(quantity))
    result = qty * unit * (1 - disc / Decimal("100"))
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
