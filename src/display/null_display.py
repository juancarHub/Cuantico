from __future__ import annotations

from .base import BaseDisplay


class NullDisplay(BaseDisplay):
    """Backend visual vacío para Windows/desarrollo/testing."""

    def __init__(self) -> None:
        self._state = "apagado"

    def set_state(self, state: str) -> None:
        if state != self._state:
            self._state = state
            print(f"🫥 Display(null) → {state}")

    def start(self) -> None:
        print("🫥 NullDisplay activo.")

    def stop(self) -> None:
        self.set_state("apagado")
        print("🫥 NullDisplay detenido.")
