from __future__ import annotations

import math
import os
import queue
import sys
import threading
import time

import interaction_state
import ui_events

from .base import BaseDisplay


EMOTIONS = {"sarcasmo", "enfadado", "cachondeo", "aburrido", "neutral"}
OPERATIONS = {"esperando", "escuchando", "pensando", "hablando", "apagado"}


class ScreenDisplay(BaseDisplay):
    """Backend visual de pantalla para tablet/Windows."""

    def __init__(self) -> None:
        self._state = "esperando"
        self._events: queue.Queue[str] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def set_state(self, state: str) -> None:
        self._state = state
        self._events.put(state)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_ui, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3.0)
        self.set_state(self._state)

    def stop(self) -> None:
        self.set_state("apagado")
        self._events.put("__quit__")
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_ui(self) -> None:
        try:
            from PySide6.QtCore import QTimer, Qt
            from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont
            from PySide6.QtWidgets import QApplication, QWidget
        except Exception as exc:
            print(f"⚠️ ScreenDisplay no disponible: {exc}")
            self._ready.set()
            return

        app = QApplication.instance() or QApplication(sys.argv[:1])
        display_mode = os.getenv("SCREEN_DISPLAY_MODE", "window").lower()

        class FaceWidget(QWidget):
            def __init__(self, events: queue.Queue[str]) -> None:
                super().__init__()
                self.events = events
                self.operation = "esperando"
                self.emotion = "neutral"
                self.t0 = time.time()
                self.setWindowTitle("Cuántico")
                self.resize(760, 520)
                self.setMinimumSize(520, 360)
                self.setStyleSheet("background: #090909;")

                self.timer = QTimer(self)
                self.timer.timeout.connect(self._tick)
                self.timer.start(16)

            def _tick(self) -> None:
                while True:
                    try:
                        event = self.events.get_nowait()
                    except queue.Empty:
                        break
                    if event == "__quit__":
                        QApplication.quit()
                        return
                    self._apply_state(event)
                self.update()

            def _apply_state(self, state: str) -> None:
                if ":" in state:
                    op, emotion = state.split(":", 1)
                    if op in OPERATIONS:
                        self.operation = op
                    if emotion in EMOTIONS:
                        self.emotion = emotion
                    return

                if state in OPERATIONS:
                    self.operation = state
                    if state == "esperando":
                        self.emotion = "neutral"
                    return

                if state in EMOTIONS:
                    self.emotion = state
                    return

                self.operation = "esperando"
                self.emotion = "neutral"

            def keyPressEvent(self, event) -> None:
                if event.key() in (Qt.Key_Escape, Qt.Key_Q):
                    QApplication.quit()

            def mousePressEvent(self, event) -> None:
                if interaction_state.is_tap_allowed():
                    ui_events.publish("screen_tap")
                event.accept()

            def _emotion_modifiers(self):
                if self.emotion == "enfadado":
                    return {"eye_w": 0.21, "eye_h": 0.11, "tilt": -0.06, "wave_amp": 0.060, "wave_freq": 3.1, "wave_speed": 6.2, "jitter": 0.65}
                if self.emotion == "cachondeo":
                    return {"eye_w": 0.24, "eye_h": 0.22, "tilt": 0.03, "wave_amp": 0.070, "wave_freq": 2.4, "wave_speed": 5.4, "jitter": 0.95}
                if self.emotion == "aburrido":
                    return {"eye_w": 0.30, "eye_h": 0.07, "tilt": 0.00, "wave_amp": 0.025, "wave_freq": 1.2, "wave_speed": 1.4, "jitter": 0.20}
                if self.emotion == "sarcasmo":
                    return {"eye_w": 0.23, "eye_h": 0.16, "tilt": 0.08, "wave_amp": 0.045, "wave_freq": 2.0, "wave_speed": 3.7, "jitter": 0.55}
                return {"eye_w": 0.22, "eye_h": 0.20, "tilt": 0.00, "wave_amp": 0.040, "wave_freq": 2.0, "wave_speed": 3.4, "jitter": 0.35}

            def paintEvent(self, event) -> None:
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing)
                w = self.width()
                h = self.height()
                t = time.time() - self.t0

                bg, face, eye, mouth = self._palette(t)
                painter.fillRect(self.rect(), QColor(*bg))

                cx = w / 2
                cy = h / 2
                r = min(w, h) * 0.34
                bob = math.sin(t * self._speed()) * r * 0.025

                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(*face)))
                painter.drawEllipse(int(cx - r), int(cy - r + bob), int(2 * r), int(2 * r))

                painter.setBrush(QBrush(QColor(*eye)))
                self._draw_eyes(painter, cx, cy + bob, r, t)

                pen = QPen(QColor(*mouth), max(5, int(r * 0.045)))
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                self._draw_mouth(painter, cx, cy + bob, r, t)

                painter.setPen(QPen(QColor(220, 220, 220, 190), 1))
                painter.setFont(QFont("Arial", max(12, int(r * 0.10))))
                painter.drawText(0, int(h - r * 0.28), w, int(r * 0.2), Qt.AlignCenter, self.operation.upper())

            def _draw_eyes(self, painter, cx: float, cy: float, r: float, t: float) -> None:
                mods = self._emotion_modifiers()
                ex = r * 0.38
                ey = r * -0.18
                eye_w, eye_h = self._eye_shape(r, t)
                tilt = mods["tilt"] * r if self.operation == "hablando" else 0
                painter.drawEllipse(int(cx - ex - eye_w / 2), int(cy + ey - eye_h / 2 + tilt), int(eye_w), int(eye_h))
                painter.drawEllipse(int(cx + ex - eye_w / 2), int(cy + ey - eye_h / 2 - tilt), int(eye_w), int(eye_h))

            def _palette(self, t: float):
                if self.operation == "esperando":
                    return (3, 20, 8), (72, 150, 65), (235, 255, 230), (235, 255, 230)
                if self.operation == "escuchando":
                    return (5, 20, 32), (30, 180, 230), (230, 255, 255), (230, 255, 255)
                if self.operation == "pensando":
                    pulse = int(35 + 20 * math.sin(t * 6))
                    return (pulse, 18, 0), (255, 160, 30), (30, 20, 10), (30, 20, 10)
                if self.operation == "hablando":
                    if self.emotion == "enfadado":
                        return (34, 0, 0), (230, 30, 30), (20, 0, 0), (20, 0, 0)
                    if self.emotion == "cachondeo":
                        return (24, 4, 35), (210, 80, 240), (255, 255, 255), (255, 255, 255)
                    if self.emotion == "aburrido":
                        return (8, 6, 20), (90, 80, 150), (20, 20, 40), (20, 20, 40)
                    return (18, 0, 0), (200, 40, 40), (255, 230, 230), (255, 230, 230)
                if self.operation == "apagado":
                    return (0, 0, 0), (25, 25, 25), (5, 5, 5), (5, 5, 5)
                return (3, 20, 8), (72, 150, 65), (235, 255, 230), (235, 255, 230)

            def _speed(self) -> float:
                return {
                    "escuchando": 4.0,
                    "pensando": 7.0,
                    "hablando": 3.2,
                    "apagado": 0.3,
                }.get(self.operation, 2.0)

            def _eye_shape(self, r: float, t: float) -> tuple[float, float]:
                if self.operation == "hablando":
                    mods = self._emotion_modifiers()
                    return r * mods["eye_w"], r * mods["eye_h"]
                if self.operation == "pensando":
                    return r * 0.18, r * 0.18
                blink = 1.0
                if int(t * 2.4) % 11 == 0:
                    blink = 0.25
                return r * 0.22, r * 0.22 * blink

            def _draw_mouth(self, painter, cx: float, cy: float, r: float, t: float) -> None:
                from PySide6.QtCore import QRectF, QPointF

                if self.operation == "escuchando":
                    painter.drawEllipse(int(cx - r * 0.13), int(cy + r * 0.22), int(r * 0.26), int(r * 0.18))
                    return
                if self.operation == "pensando":
                    dots = "." * (1 + int(t * 3) % 3)
                    painter.setFont(QFont("Arial", max(20, int(r * 0.28)), QFont.Bold))
                    painter.drawText(int(cx - r * 0.4), int(cy + r * 0.05), int(r * 0.8), int(r * 0.35), Qt.AlignCenter, dots)
                    return
                if self.operation == "hablando":
                    mods = self._emotion_modifiers()
                    width = r * 0.62
                    amp = r * mods["wave_amp"]
                    mid_y = cy + r * 0.30
                    points = []
                    for i in range(36):
                        x = cx - width / 2 + width * i / 35
                        phase = (i / 35) * math.tau * mods["wave_freq"]
                        y = mid_y + amp * math.sin(phase + t * mods["wave_speed"]) + amp * mods["jitter"] * math.sin(phase * 2.3 - t * (mods["wave_speed"] * 0.55))
                        points.append(QPointF(x, y))
                    for a, b in zip(points, points[1:]):
                        painter.drawLine(a, b)
                    return
                if self.operation == "apagado":
                    painter.drawLine(int(cx - r * 0.18), int(cy + r * 0.28), int(cx + r * 0.18), int(cy + r * 0.28))
                    return

                rect = QRectF(cx - r * 0.35, cy + r * 0.06, r * 0.70, r * 0.42)
                painter.drawArc(rect, 200 * 16, 140 * 16)

        widget = FaceWidget(self._events)
        if display_mode in ("fullscreen", "full", "tablet"):
            widget.showFullScreen()
        else:
            widget.show()
        self._ready.set()
        app.exec()
