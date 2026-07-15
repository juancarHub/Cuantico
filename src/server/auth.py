from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, WebSocket

from .settings import api_token, node_tokens


def _matches(received: str, expected: str) -> bool:
    return bool(expected) and hmac.compare_digest(received, expected)


async def require_api_token(authorization: str | None = Header(default=None)) -> None:
    expected = api_token()
    if not expected:
        raise HTTPException(503, "CUANTICO_API_TOKEN no esta configurado")
    received = ""
    if authorization and authorization.lower().startswith("bearer "):
        received = authorization[7:].strip()
    if not _matches(received, expected):
        raise HTTPException(401, "Token no valido")


def require_event_token(authorization: str | None, source: str) -> None:
    received = ""
    if authorization and authorization.lower().startswith("bearer "):
        received = authorization[7:].strip()
    tokens = node_tokens()
    expected_node_token = tokens.get(source) or tokens.get("*")
    if _matches(received, api_token()) or _matches(received, expected_node_token or ""):
        return
    raise HTTPException(401, "Token de nodo no valido")


async def websocket_authorized(websocket: WebSocket, source: str) -> bool:
    tokens = node_tokens()
    expected = tokens.get(source) or tokens.get("*") or api_token()
    received = websocket.query_params.get("token", "")
    if _matches(received, expected):
        return True
    await websocket.close(code=1008, reason="Token no valido")
    return False
