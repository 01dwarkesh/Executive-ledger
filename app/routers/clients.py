from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.client import Client
from app.models.user import User
from app.schemas.client_schema import ClientCreate, ClientUpdate, ClientOut
from app.dependencies.auth_dependencies import get_current_user, apply_ownership_filter

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("/", response_model=List[ClientOut])
async def list_clients(
    search: Optional[str] = Query(None, description="Search by company or contact name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Client)
    q = apply_ownership_filter(q, Client, current_user)
    if search:
        q = q.where(or_(
            Client.company_name.ilike(f"%{search}%"),
            Client.contact_name.ilike(f"%{search}%"),
            Client.email.ilike(f"%{search}%"),
        ))
    q = q.order_by(Client.company_name).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/", response_model=ClientOut, status_code=201)
async def create_client(
    payload: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = Client(**payload.model_dump(), created_by=current_user.id)
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Client).where(Client.id == client_id)
    q = apply_ownership_filter(q, Client, current_user)
    result = await db.execute(q)
    client = result.scalar_one_or_none()
    if not client:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Client not found.")
    return client


@router.put("/{client_id}", response_model=ClientOut)
async def update_client(
    client_id: str,
    payload: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Client).where(Client.id == client_id)
    q = apply_ownership_filter(q, Client, current_user)
    result = await db.execute(q)
    client = result.scalar_one_or_none()
    if not client:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Client not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(client, field, value)
    await db.commit()
    await db.refresh(client)
    return client


@router.delete("/{client_id}", response_model=dict)
async def delete_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Client).where(Client.id == client_id)
    q = apply_ownership_filter(q, Client, current_user)
    result = await db.execute(q)
    client = result.scalar_one_or_none()
    if not client:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Client not found.")
    await db.delete(client)
    await db.commit()
    return {"message": "Client deleted."}


@router.get("/stats/summary", response_model=dict)
async def client_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(func.count(Client.id))
    q = apply_ownership_filter(q, Client, current_user)
    total = (await db.execute(q)).scalar_one()
    return {"total_clients": total}