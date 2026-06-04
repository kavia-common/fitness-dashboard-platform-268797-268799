from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models import AppUser, UserRole
from app.db.session import get_db

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def _get_user_by_id(db: AsyncSession, user_id) -> Optional[AppUser]:
    result = await db.execute(select(AppUser).where(AppUser.id == user_id))
    return result.scalar_one_or_none()


# PUBLIC_INTERFACE
async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> AppUser:
    """Resolve the current user from Bearer token."""
    try:
        user_id = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await _get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


# PUBLIC_INTERFACE
async def require_admin(
    user: Annotated[AppUser, Depends(get_current_user)],
) -> AppUser:
    """Require current user to have admin role."""
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


# PUBLIC_INTERFACE
def get_ws_token(token: Annotated[str, Query(..., description="JWT token as query param for WebSocket auth")]) -> str:
    """Dependency to document WebSocket token query param."""
    return token
