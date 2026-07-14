from __future__ import annotations

import asyncio
from collections import defaultdict, deque

from fastapi import WebSocket

from .schemas import EventPayload


class NodeRegistry:
    def __init__(self, max_pending_per_node: int = 100) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._pending: dict[str, deque[EventPayload]] = defaultdict(
            lambda: deque(maxlen=max_pending_per_node)
        )
        self._lock = asyncio.Lock()

    async def connect(self, source: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            previous = self._connections.get(source)
            self._connections[source] = websocket
            pending = list(self._pending.pop(source, ()))
        if previous is not None and previous is not websocket:
            await previous.close(code=1012, reason="Nodo reconectado")
        for command in pending:
            await websocket.send_json(command)

    async def disconnect(self, source: str, websocket: WebSocket) -> None:
        async with self._lock:
            if self._connections.get(source) is websocket:
                del self._connections[source]

    async def send_or_queue(self, source: str, command: EventPayload) -> bool:
        async with self._lock:
            websocket = self._connections.get(source)
            if websocket is None:
                self._pending[source].append(dict(command))
                return False
        try:
            await websocket.send_json(command)
            return True
        except Exception:
            async with self._lock:
                if self._connections.get(source) is websocket:
                    del self._connections[source]
                self._pending[source].appendleft(dict(command))
            return False

    async def connected_sources(self) -> list[str]:
        async with self._lock:
            return sorted(self._connections)
