from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification, NotificationType
from app.realtime.manager import manager

logger = logging.getLogger(__name__)


# PUBLIC_INTERFACE
async def create_notification(
    db: AsyncSession,
    *,
    user_id: UUID,
    type: NotificationType,
    title: str,
    message: str,
    payload: Optional[dict[str, Any]] = None,
    push_ws: bool = True,
) -> Notification:
    """Create a notification row and (optionally) push it over WebSocket."""
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        payload=payload or {},
        is_read=False,
        created_at=datetime.now(timezone.utc),
        read_at=None,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)

    if push_ws:
        await manager.send_to_user(
            user_id,
            {
                "type": "notification.created",
                "notification": {
                    "id": str(notif.id),
                    "type": notif.type.value,
                    "title": notif.title,
                    "message": notif.message,
                    "payload": notif.payload,
                    "is_read": notif.is_read,
                    "created_at": notif.created_at.isoformat(),
                },
            },
        )
    return notif


# PUBLIC_INTERFACE
async def list_notifications(db: AsyncSession, *, user_id: UUID, limit: int = 50) -> list[Notification]:
    """List recent notifications for a user."""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
