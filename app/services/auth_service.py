from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.schemas.user_schema import UserCreate, UserUpdate, UserPasswordReset
from app.utils.token_utils import hash_password, verify_password, create_access_token


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User:
    """
    Looks up user by email and verifies bcrypt password.
    Raises 401 on bad credentials, 403 if deactivated.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )
    return user


def build_token(user: User) -> str:
    """Creates a JWT with user id and role embedded."""
    return create_access_token({
        "sub": str(user.id),
        "role": user.role.value,
        "email": user.email,
    })


async def create_user(payload: UserCreate, db: AsyncSession) -> User:
    """Admin-only: creates a new user. Raises 409 on duplicate email."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{payload.email}' already exists.",
        )
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(user_id: str, payload: UserUpdate, db: AsyncSession) -> User:
    """Admin-only: update name, role, or active status."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


async def reset_user_password(user_id: str, payload: UserPasswordReset, db: AsyncSession) -> None:
    """Admin-only: forcefully reset any user's password."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.hashed_password = hash_password(payload.new_password)
    await db.commit()


async def deactivate_user(user_id: str, requesting_admin_id: str, db: AsyncSession) -> None:
    """Admin-only: deactivate a user. Cannot deactivate yourself."""
    if str(user_id) == str(requesting_admin_id):
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = False
    await db.commit()


async def reactivate_user(user_id: str, db: AsyncSession) -> User:
    """Admin-only: re-enable a deactivated user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = True
    await db.commit()
    await db.refresh(user)
    return user