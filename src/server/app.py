from __future__ import annotations

from collections.abc import Callable
import asyncio

from fastapi import Depends, FastAPI, Header, Query, WebSocket, WebSocketDisconnect

from .auth import require_api_token, require_event_token, websocket_authorized
from .node_registry import NodeRegistry
from .settings import world_db_path
from .schemas import (
    AcceptedEvent,
    DeliveryResult,
    HealthResponse,
    NodeEvent,
    SpeakCommand,
)
from world import WorldStore


app = FastAPI(title="Cuantico Node API", version="0.1.0")
nodes = NodeRegistry()
world = WorldStore(world_db_path())
world.initialize()
_event_handler: Callable[[dict], None] | None = None


def set_event_handler(handler: Callable[[dict], None] | None) -> None:
    global _event_handler
    _event_handler = handler


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        connected_nodes=await nodes.connected_sources(),
        received_events=world.event_count(),
    )


@app.post(
    "/api/v1/events",
    response_model=AcceptedEvent,
)
async def receive_event(
    event: NodeEvent,
    authorization: str | None = Header(default=None),
) -> AcceptedEvent:
    require_event_token(authorization, event.source)
    payload = event.model_dump(exclude_none=True)
    inserted = await asyncio.to_thread(world.ingest, payload)
    if inserted and _event_handler is not None:
        _event_handler(dict(payload))
    return AcceptedEvent(event_id=event.event_id)


@app.get("/api/v1/events", dependencies=[Depends(require_api_token)])
async def recent_events(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return await asyncio.to_thread(world.recent_events, limit)


@app.get("/api/v1/world", dependencies=[Depends(require_api_token)])
async def world_snapshot() -> dict:
    return await asyncio.to_thread(world.snapshot)


@app.get("/api/v1/world/rooms/{room}", dependencies=[Depends(require_api_token)])
async def world_room(room: str) -> dict:
    return await asyncio.to_thread(world.room, room) or {"room": room, "status": "unknown"}


@app.post(
    "/api/v1/nodes/{source}/speak",
    response_model=DeliveryResult,
    dependencies=[Depends(require_api_token)],
)
async def speak_to_node(source: str, command: SpeakCommand) -> DeliveryResult:
    payload = command.model_dump(exclude_none=True)
    payload["target_source"] = source
    connected = await nodes.send_or_queue(source, payload)
    return DeliveryResult(
        status="sent" if connected else "queued",
        target_source=source,
        event_id=command.event_id,
        connected=connected,
    )


@app.websocket("/api/v1/nodes/{source}/stream")
async def node_stream(websocket: WebSocket, source: str) -> None:
    if not await websocket_authorized(websocket, source):
        return
    await nodes.connect(source, websocket)
    try:
        while True:
            message = await websocket.receive_json()
            if isinstance(message, dict):
                message.setdefault("source", source)
                await asyncio.to_thread(world.ingest, message)
                if _event_handler is not None:
                    _event_handler(dict(message))
    except WebSocketDisconnect:
        pass
    finally:
        await nodes.disconnect(source, websocket)
