from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, DefaultDict, Set
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """In-memory WebSocket connection manager keyed by user id.

    Suitable for a single-process demo deployment. For multi-replica deployments,
    replace with Redis pub/sub or another shared broker.
    """

    def __init__(self) -> None:
        self._connections: DefaultDict[UUID, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[user_id].add(websocket)
        logger.info("WS connected user_id=%s", user_id)

    async def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            if user_id in self._connections and websocket in self._connections[user_id]:
                self._connections[user_id].remove(websocket)
                if not self._connections[user_id]:
                    self._connections.pop(user_id, None)
        logger.info("WS disconnected user_id=%s", user_id)

    async def send_to_user(self, user_id: UUID, event: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._connections.get(user_id, set()))
        for ws in sockets:
            try:
                await ws.send_json(event)
            except Exception as exc:
                logger.warning("WS send failed user_id=%s err=%s", user_id, exc)

    async def broadcast(self, event: dict[str, Any]) -> None:
        async with self._lock:
            pairs = [(uid, ws) for uid, sockets in self._connections.items() for ws in sockets]
        for _, ws in pairs:
            try:
                await ws.send_json(event)
            except Exception:
                # ignore individual failures
                pass


manager = ConnectionManager()
