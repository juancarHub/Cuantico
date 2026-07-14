from __future__ import annotations

import asyncio
from collections import deque

from .schemas import EventPayload


class EventStore:
    def __init__(self, max_events: int = 500) -> None:
        self._events: deque[EventPayload] = deque(maxlen=max_events)
        self._lock = asyncio.Lock()

    async def append(self, event: EventPayload) -> None:
        async with self._lock:
            self._events.append(dict(event))

    async def recent(self, limit: int = 50) -> list[EventPayload]:
        async with self._lock:
            return list(self._events)[-max(1, min(limit, 200)) :]

    async def count(self) -> int:
        async with self._lock:
            return len(self._events)
