from __future__ import annotations

import config

from .null_display import NullDisplay


def create_display():
    backend = config.DISPLAY_BACKEND

    print(f"🖥️ Display backend configurado: {backend}")

    if backend in ("null", "none"):
        return NullDisplay()

    if backend in ("screen", "tablet", "windows"):
        try:
            from .screen_display import ScreenDisplay

            print("🖥️ Backend visual ScreenDisplay cargado.")
            return ScreenDisplay()
        except Exception as exc:
            print(f"⚠️ ScreenDisplay no disponible: {exc}")

    if backend in ("neopixel", "raspberry", "auto"):
        try:
            from .neopixel_display import NeoPixelDisplay

            print("💡 Backend visual NeoPixel cargado.")
            return NeoPixelDisplay()
        except Exception as exc:
            print(f"⚠️ NeoPixel no disponible: {exc}")

    print("💡 Fallback a NullDisplay.")
    return NullDisplay()
