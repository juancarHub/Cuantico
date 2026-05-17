from __future__ import annotations

import threading

_STATE = "idle"
_lock = threading.Lock()


def set_state(state: str):
    global _STATE
    with _lock:
        _STATE = state


def get_state() -> str:
    with _lock:
        return _STATE


def is_tap_allowed() -> bool:
    return get_state() in ("idle", "listening")


def is_idle() -> bool:
    return get_state() == "idle"


def is_listening() -> bool:
    return get_state() == "listening"
