import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import engine, Base
from app.routers import auth, clients, quotes, quote_items, public_quote, import_csv, export_pdf, products

logging.basicConfig(level=logging.INFO)
logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.getLogger("weasyprint").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.models import user, client, product, quote, quote_item, activity_log  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified.")

    await _seed_admin_and_products()
    logger.info("Startup complete.")

    yield

    await engine.dispose()
    logger.info("DB engine disposed.")


async def _seed_admin_and_products():
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.user import User, UserRole
    from app.models.product import Product
    from app.utils.token_utils import hash_password

    async with AsyncSessionLocal() as db:
        existing_admin = (
            await db.execute(select(User).where(User.role == UserRole.admin))
        ).scalars().first()

        if not existing_admin:
            db.add(User(
                email="admin@example.com",
                hashed_password=hash_password("Admin@123"),
                full_name="Ledger Admin",
                role=UserRole.admin,
            ))
            await db.flush()
            logger.info("Default admin created: admin@example.com / Admin@123")

        product_exists = (await db.execute(select(Product))).scalars().first()
        if not product_exists:
            seed_products = [
                ("Ceramic Mug", "Drinkware"),
                ("T-Shirt", "Apparel"),
                ("Polo Shirt", "Apparel"),
                ("Hoodie", "Apparel"),
                ("Tote Bag", "Bags"),
                ("Cap/Hat", "Headwear"),
                ("Water Bottle", "Drinkware"),
                ("Notebook", "Stationery"),
            ]
            for name, category in seed_products:
                db.add(Product(name=name, category=category))
            logger.info("8 seed products created.")

        await db.commit()


limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title="Sales Quote API",
    version="1.0.0",
    description="B2B Sales Quoting SaaS — internal quoting platform.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

API = "/api/v1"
app.include_router(auth.router,         prefix=API)
app.include_router(clients.router,      prefix=API)
app.include_router(products.router,     prefix=API)
app.include_router(quotes.router,       prefix=API)
app.include_router(quote_items.router,  prefix=API)
app.include_router(public_quote.router, prefix=API)
app.include_router(import_csv.router,   prefix=API)
app.include_router(export_pdf.router,   prefix=API)


@app.get("/api/v1/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
