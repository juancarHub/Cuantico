from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable

import uvicorn

from .app import app, nodes, set_event_handler
from .settings import host, port


class EmbeddedServer:
    def __init__(self, on_event: Callable[[dict], None]) -> None:
        self.on_event = on_event
        self.loop: asyncio.AbstractEventLoop | None = None
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        set_event_handler(self.on_event)
        self.thread = threading.Thread(target=self._run, daemon=True, name="cuantico_api")
        self.thread.start()
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if self.server is not None and self.server.started:
                print(f"API de nodos activa en {host()}:{port()}")
                return
            if self.thread is not None and not self.thread.is_alive():
                break
            time.sleep(0.05)
        raise RuntimeError(
            "No se pudo iniciar la API integrada. Cierra Run_Server.bat si usa el puerto 8000."
        )

    def _run(self) -> None:
        asyncio.run(self._serve())

    async def _serve(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.server = uvicorn.Server(
            uvicorn.Config(app, host=host(), port=port(), log_level="info")
        )
        await self.server.serve()

    def send_to_node(self, source: str, command: dict) -> bool:
        if self.loop is None:
            return False
        future = asyncio.run_coroutine_threadsafe(
            nodes.send_or_queue(source, command), self.loop
        )
        return bool(future.result(timeout=5.0))

    def stop(self) -> None:
        set_event_handler(None)
        if self.server is not None:
            self.server.should_exit = True
        if self.thread is not None:
            self.thread.join(timeout=3.0)
