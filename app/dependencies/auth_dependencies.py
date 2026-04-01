from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db
from app.models.user import User, UserRole
from app.utils.token_utils import decode_token

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decodes the Bearer JWT and returns the matching active User.
    Raises 401 if token is missing, expired, or invalid.
    Raises 403 if account is deactivated.
    """
    exc_401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if not user_id:
            raise exc_401
    except JWTError:
        raise exc_401

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise exc_401
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Contact your administrator.",
        )
    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Raises 403 if the current user is not an admin.
    Use as a FastAPI dependency on any admin-only route.
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


async def require_active_sales(
    current_user: User = Depends(get_current_user),
) -> User:
    """Allows both admin and sales — just must be active (covered by get_current_user)."""
    return current_user


def apply_ownership_filter(query, model, current_user: User):
    """
    If current user is a sales user, filter query to rows they own.
    If admin, return query unchanged (sees everything).
    """
    if current_user.role != UserRole.admin:
        query = query.where(model.created_by == current_user.id)
    return query