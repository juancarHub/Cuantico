from __future__ import annotations

from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect

from .auth import require_api_token, websocket_authorized
from .event_store import EventStore
from .node_registry import NodeRegistry
from .schemas import (
    AcceptedEvent,
    DeliveryResult,
    HealthResponse,
    NodeEvent,
    SpeakCommand,
)


app = FastAPI(title="Cuantico Node API", version="0.1.0")
events = EventStore()
nodes = NodeRegistry()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        connected_nodes=await nodes.connected_sources(),
        received_events=await events.count(),
    )


@app.post(
    "/api/v1/events",
    response_model=AcceptedEvent,
    dependencies=[Depends(require_api_token)],
)
async def receive_event(event: NodeEvent) -> AcceptedEvent:
    await events.append(event.model_dump(exclude_none=True))
    return AcceptedEvent(event_id=event.event_id)


@app.get("/api/v1/events", dependencies=[Depends(require_api_token)])
async def recent_events(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return await events.recent(limit)


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
                await events.append(message)
    except WebSocketDisconnect:
        pass
    finally:
        await nodes.disconnect(source, websocket)
