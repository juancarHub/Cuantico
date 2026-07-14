from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def api_token() -> str:
    return os.getenv("CUANTICO_API_TOKEN", "").strip()


def node_tokens() -> dict[str, str]:
    raw = os.getenv("CUANTICO_NODE_TOKENS", "").strip()
    tokens: dict[str, str] = {}
    for item in raw.split(","):
        if not item.strip() or ":" not in item:
            continue
        source, token = item.split(":", 1)
        if source.strip() and token.strip():
            tokens[source.strip()] = token.strip()
    return tokens


def host() -> str:
    return os.getenv("CUANTICO_SERVER_HOST", "0.0.0.0").strip()


def port() -> int:
    return int(os.getenv("CUANTICO_SERVER_PORT", "8000"))
