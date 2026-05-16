from __future__ import annotations

import math
import random
import threading
import time

import board
import neopixel

from .base import BaseDisplay

NUM_PIXELS = 12
PIN_LEDS = board.D12
BRIGHTNESS = 0.2


class NeoPixelDisplay(BaseDisplay):
    def __init__(self) -> None:
        self._pixels = neopixel.NeoPixel(
            PIN_LEDS,
            NUM_PIXELS,
            brightness=BRIGHTNESS,
            auto_write=False,
        )
        self._state = "esperando"
        self._thread = None

    def set_state(self, state: str) -> None:
        self._state = state

    def start(self) -> None:
        if self._thread:
            return

        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.set_state("apagado")
        if self._thread:
            self._thread.join(timeout=1.0)

    def _animate(self) -> None:
        while True:
            if self._state == "esperando":
                val = (math.sin(time.time() * 2) + 1) / 2
                self._pixels.fill((int(val * 100) + 10, 0, 0))
                self._pixels.show()
                time.sleep(0.02)

            elif self._state == "escuchando":
                val = (math.sin(time.time() * 4) + 1) / 2
                self._pixels.fill((0, int(val * 150) + 20, int(val * 200) + 40))
                self._pixels.show()
                time.sleep(0.02)

            elif self._state == "pensando":
                self._pixels.fill((0, 0, 0))
                for i in range(3):
                    idx = (int(time.time() * 15) + i) % NUM_PIXELS
                    self._pixels[idx] = (255, 100, 0)
                self._pixels.show()
                time.sleep(0.05)

            elif self._state == "sarcasmo":
                val = (math.sin(time.time() * 8) + 1) / 2
                self._pixels.fill((int(val * 200) + 55, 0, 0))
                self._pixels.show()
                time.sleep(0.02)

            elif self._state == "enfadado":
                self._pixels.fill((random.randint(150, 255), 0, 0))
                self._pixels.show()
                time.sleep(random.uniform(0.02, 0.08))
                self._pixels.fill((10, 0, 0))
                self._pixels.show()
                time.sleep(random.uniform(0.02, 0.08))

            elif self._state == "cachondeo":
                for i in range(NUM_PIXELS):
                    hue = (int(time.time() * 100) + (i * 256 // NUM_PIXELS)) % 256
                    self._pixels[i] = (hue, 255 - hue, 128)
                self._pixels.show()
                time.sleep(0.02)

            elif self._state == "aburrido":
                val = (math.sin(time.time() * 1) + 1) / 2
                self._pixels.fill((int(val * 40), 0, int(val * 60)))
                self._pixels.show()
                time.sleep(0.05)

            elif self._state == "apagado":
                self._pixels.fill((0, 0, 0))
                self._pixels.show()
                break
