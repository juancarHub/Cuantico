from __future__ import annotations

import os

from .null_display import NullDisplay


def create_display():
    backend = os.getenv("DISPLAY_BACKEND", "auto").lower()

    if backend in ("null", "none"):
        return NullDisplay()

    if backend in ("neopixel", "raspberry", "auto"):
        try:
            from .neopixel_display import NeoPixelDisplay

            print("💡 Backend visual NeoPixel cargado.")
            return NeoPixelDisplay()
        except Exception as exc:
            print(f"⚠️ NeoPixel no disponible: {exc}")

    print("💡 Fallback a NullDisplay.")
    return NullDisplay()
