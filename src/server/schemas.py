from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NodeEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    event: str
    source: str
    timestamp: str = Field(default_factory=lambda: datetime.now().astimezone().isoformat())
    event_id: str | None = None
    room: str | None = None


class SpeakCommand(BaseModel):
    event: str = "node_speak"
    event_id: str
    text: str = Field(min_length=1, max_length=4000)
    priority: str = "normal"
    voice: str | None = None


class AcceptedEvent(BaseModel):
    status: str = "accepted"
    event_id: str | None = None


class DeliveryResult(BaseModel):
    status: str
    target_source: str
    event_id: str
    connected: bool


class HealthResponse(BaseModel):
    status: str = "ok"
    connected_nodes: list[str]
    received_events: int


EventPayload = dict[str, Any]
