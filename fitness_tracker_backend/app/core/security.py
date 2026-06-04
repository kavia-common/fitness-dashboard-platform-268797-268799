from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return _pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return _pwd_context.verify(password, password_hash)


# PUBLIC_INTERFACE
def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The token subject (user id as string UUID).
        expires_minutes: Optional override expiration in minutes.

    Returns:
        Signed JWT string.
    """
    expire_mins = expires_minutes if expires_minutes is not None else settings.access_token_expire_minutes
    exp = datetime.now(timezone.utc) + timedelta(minutes=expire_mins)
    payload = {"sub": subject, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# PUBLIC_INTERFACE
def decode_access_token(token: str) -> UUID:
    """Decode and validate a JWT access token and return the user id (UUID)."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            raise ValueError("Token missing subject")
        return UUID(sub)
    except (JWTError, ValueError) as exc:
        logger.info("JWT decode failed: %s", exc)
        raise
