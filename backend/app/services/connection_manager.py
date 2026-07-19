"""Gestionnaire de connexions WebSocket par cookbook."""

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Gere les WebSocket groupes par cookbook_id."""

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, cookbook_id: int, websocket: WebSocket) -> None:
        # L appelant doit deja avoir fait accept()
        async with self._lock:
            self._connections[cookbook_id].add(websocket)

    def disconnect(self, cookbook_id: int, websocket: WebSocket) -> None:
        self._connections[cookbook_id].discard(websocket)
        if not self._connections[cookbook_id]:
            del self._connections[cookbook_id]

    async def broadcast(self, cookbook_id: int, message: dict[str, Any]) -> None:
        sockets = list(self._connections.get(cookbook_id, []))
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(cookbook_id, ws)


manager = ConnectionManager()
