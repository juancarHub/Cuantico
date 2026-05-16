from __future__ import annotations


class BaseDisplay:
    """Interfaz visual abstracta para Cuántico."""

    def set_state(self, state: str) -> None:
        raise NotImplementedError

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError
