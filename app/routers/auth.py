from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user_schema import (
    LoginRequest, TokenOut, UserOut,
    UserCreate, UserUpdate, UserPasswordReset,
)
from app.services import auth_service
from app.dependencies.auth_dependencies import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=201, summary="Register user (admin-only after first user)")
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    If no users exist → open registration (bootstrapping first admin).
    If users exist → requires Bearer token with admin role.
    """
    user_count = (await db.execute(select(func.count(User.id)))).scalar_one()
    if user_count > 0:
        # After first user, require admin token
        from fastapi import Request
        raise HTTPException(
            status_code=403,
            detail="Use POST /api/v1/auth/users with admin token to create more users."
        )
    return await auth_service.create_user(payload, db)


@router.post("/login", response_model=TokenOut, summary="Login with email + password")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(payload.email, payload.password, db)
    token = auth_service.build_token(user)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut, summary="Get current user profile")
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=List[UserOut], summary="[Admin] List all users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.get("/users/{user_id}", response_model=UserOut, summary="[Admin] Get a single user")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.post("/users", response_model=UserOut, status_code=201, summary="[Admin] Create a new user")
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return await auth_service.create_user(payload, db)


@router.put("/users/{user_id}", response_model=UserOut, summary="[Admin] Update user")
async def update_user(
    user_id: str,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return await auth_service.update_user(user_id, payload, db)


@router.post("/users/{user_id}/reset-password", response_model=dict, summary="[Admin] Reset password")
async def reset_password(
    user_id: str,
    payload: UserPasswordReset,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    await auth_service.reset_user_password(user_id, payload, db)
    return {"message": "Password reset successfully."}


@router.post("/users/{user_id}/deactivate", response_model=dict, summary="[Admin] Deactivate user")
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    await auth_service.deactivate_user(user_id, str(admin.id), db)
    return {"message": "User deactivated."}


@router.post("/users/{user_id}/reactivate", response_model=UserOut, summary="[Admin] Reactivate user")
async def reactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return await auth_service.reactivate_user(user_id, db)
