from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import router as api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.security import decode_access_token
from app.db.models import AppUser
from app.db.session import get_db
from app.realtime.manager import manager

configure_logging()
logger = logging.getLogger(__name__)

openapi_tags = [
    {"name": "auth", "description": "Authentication and user identity."},
    {"name": "profile", "description": "User profile and onboarding preferences."},
    {"name": "goals", "description": "Goal management."},
    {"name": "plan", "description": "Workout plan retrieval and regeneration."},
    {"name": "workouts", "description": "Workout logging."},
    {"name": "nutrition", "description": "Nutrition logging (optional)."},
    {"name": "progress", "description": "Progress aggregation and dashboard summaries."},
    {"name": "notifications", "description": "Notification list and test push helpers."},
    {"name": "content", "description": "Public content pages."},
    {"name": "admin", "description": "Admin-only content management."},
    {"name": "realtime", "description": "WebSocket endpoints for real-time notifications."},
]


app = FastAPI(
    title="Fitness Tracker Backend API",
    description=(
        "FastAPI backend for the Personalized Fitness Tracker.\n\n"
        "WebSocket usage:\n"
        "- Connect to `/ws/notifications?token=<JWT>` to receive real-time events.\n"
        "- Events include `notification.created`, `plan.regenerated`, `progress.updated`.\n"
    ),
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# CORS
origins = settings.cors_origin_list()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get(
    "/health",
    tags=["system"],
    summary="Health check",
    description="Basic health endpoint for container orchestration.",
    operation_id="health_check",
)
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get(
    "/docs/ws",
    tags=["realtime"],
    summary="WebSocket usage instructions",
    description="Returns a short guide for connecting to the notifications WebSocket endpoint.",
    operation_id="ws_usage_docs",
)
def ws_usage_docs() -> dict:
    """Return WebSocket usage instructions."""
    return {
        "websocket_url_template": "/ws/notifications?token=<JWT>",
        "notes": [
            "Pass the JWT access token as a query parameter.",
            "This demo uses in-memory connection tracking; scale-out requires a shared broker.",
        ],
        "event_types": ["notification.created"],
    }


async def _get_user_for_ws(db: AsyncSession, token: str) -> AppUser:
    """Validate token and return user for WS connections."""
    user_id = decode_access_token(token)
    res = await db.execute(select(AppUser).where(AppUser.id == user_id))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise ValueError("User not found or inactive")
    return user


@app.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, token: str, db: AsyncSession = Depends(get_db)) -> None:
    """WebSocket endpoint for real-time notifications.

    Parameters:
        websocket: The client WebSocket connection.
        token: JWT access token passed as a query parameter.

    Behavior:
        - Accepts the socket if the token is valid.
        - Sends JSON events for notifications and other updates.
    """
    try:
        user = await _get_user_for_ws(db, token)
    except Exception:
        await websocket.close(code=1008)
        return

    await manager.connect(user.id, websocket)
    try:
        # Keep alive loop. We don't require client messages, but we read to detect disconnects.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(user.id, websocket)
    except Exception:
        await manager.disconnect(user.id, websocket)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
