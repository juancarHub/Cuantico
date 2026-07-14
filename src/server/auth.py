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


async def websocket_authorized(websocket: WebSocket, source: str) -> bool:
    expected = node_tokens().get(source) or api_token()
    received = websocket.query_params.get("token", "")
    if _matches(received, expected):
        return True
    await websocket.close(code=1008, reason="Token no valido")
    return False
