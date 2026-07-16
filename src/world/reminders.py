from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo

from .store import WorldStore


NotificationCallback = Callable[[str, str], None]
_FOREVER = "9999-12-31T23:59:59+00:00"


class ReminderService:
    def __init__(
        self,
        world: WorldStore,
        callback: NotificationCallback,
        poll_seconds: float = 0.5,
    ) -> None:
        self.world = world
        self.callback = callback
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="cuantico-reminders",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def notify_changed(self) -> None:
        self._wake.set()

    def handle_event(self, event: dict) -> int:
        matched = self.world.claim_event_schedules(event)
        for schedule in matched:
            message = _event_notification(schedule["payload"], event)
            self.callback(message, "atento")
        return len(matched)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                for schedule in self.world.claim_due_schedules():
                    message = schedule["payload"].get("message") or "Se ha cumplido el plazo."
                    self.callback(message, "atento")
            except Exception as exc:
                print(f"Avisos: error revisando vencimientos: {exc}")
            self._wake.wait(self.poll_seconds)
            self._wake.clear()


def build_reminder_tools(world: WorldStore, service: ReminderService) -> list:
    def crear_aviso_en(segundos: int, mensaje: str) -> str:
        """Crea un aviso persistente dentro de N segundos. Convierte antes horas o minutos a segundos. El mensaje debe explicar exactamente que debe recordar al usuario."""
        seconds = max(1, int(segundos))
        execute_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        schedule_id = world.create_schedule(
            "reminder_time",
            execute_at.isoformat(),
            {"message": mensaje.strip() or "Se ha cumplido el plazo."},
        )
        service.notify_changed()
        return f"ok: aviso {schedule_id} programado dentro de {seconds} segundos"

    def crear_aviso_fecha(fecha_hora_iso: str, mensaje: str) -> str:
        """Crea un aviso persistente para una fecha y hora exactas. Usa ISO 8601 con zona horaria, por ejemplo 2026-07-16T20:30:00+02:00."""
        parsed = datetime.fromisoformat(fecha_hora_iso.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()
        if parsed.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            return "fallo: la fecha del aviso ya ha pasado"
        schedule_id = world.create_schedule(
            "reminder_time",
            parsed.astimezone(timezone.utc).isoformat(),
            {"message": mensaje.strip() or "Se ha cumplido el plazo."},
        )
        service.notify_changed()
        return f"ok: aviso {schedule_id} programado para {parsed.isoformat()}"

    def crear_aviso_diario(hora_hhmm: str, mensaje: str) -> str:
        """Crea un aviso persistente que se repite todos los dias a una hora local HH:MM, por ejemplo 13:00."""
        parts = hora_hhmm.strip().replace(".", ":").split(":")
        if len(parts) != 2:
            return "fallo: usa una hora con formato HH:MM"
        hour, minute = int(parts[0]), int(parts[1])
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            return "fallo: la hora debe estar entre 00:00 y 23:59"
        local_zone = ZoneInfo("Europe/Madrid")
        now_local = datetime.now(local_zone)
        execute_at = now_local.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )
        if execute_at <= now_local:
            execute_at += timedelta(days=1)
        schedule_id = world.create_schedule(
            "reminder_time",
            execute_at.astimezone(timezone.utc).isoformat(),
            {
                "message": mensaje.strip() or "Ha llegado la hora del aviso diario.",
                "recurrence": "daily",
                "hour": hour,
                "minute": minute,
                "timezone": "Europe/Madrid",
            },
        )
        service.notify_changed()
        return f"ok: aviso diario {schedule_id} programado a las {hour:02d}:{minute:02d}"

    def crear_aviso_evento(
        evento: str,
        habitacion: str = "",
        persona: str = "",
        mensaje: str = "",
        durante_segundos: int = 0,
        mantener: bool = False,
    ) -> str:
        """Avisa cuando llegue un evento de nodo. Para una entrada usa evento='person_presence_confirmed'; para una salida, 'person_exit_confirmed'. habitacion y persona son filtros opcionales. durante_segundos=0 espera sin caducidad. mantener=true conserva la tarea tras cada aviso."""
        duration = max(0, int(durante_segundos))
        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=duration)
        ).isoformat() if duration else _FOREVER
        payload = {
            "event": evento.strip(),
            "room": habitacion.strip(),
            "person": persona.strip(),
            "message": mensaje.strip() or _default_event_message(evento, habitacion, persona),
            "duration_seconds": duration,
            "repeat": bool(mantener),
        }
        schedule_id = world.create_schedule("reminder_event", expires_at, payload)
        mode = "permanente" if mantener else "de una sola vez"
        return f"ok: aviso de evento {schedule_id} creado ({mode})"

    def listar_avisos() -> str:
        """Lista los avisos de tiempo y de eventos que siguen pendientes."""
        schedules = world.schedules()
        return json.dumps(schedules, ensure_ascii=False) if schedules else "no hay avisos pendientes"

    def cancelar_aviso(id_o_texto: str) -> str:
        """Cancela avisos pendientes por su id o por parte del mensaje."""
        count = world.cancel_schedule(id_o_texto)
        service.notify_changed()
        return f"ok: cancelados {count} aviso(s)" if count else "fallo: no encuentro ese aviso"

    return [
        crear_aviso_en,
        crear_aviso_fecha,
        crear_aviso_diario,
        crear_aviso_evento,
        listar_avisos,
        cancelar_aviso,
    ]


def _default_event_message(event: str, room: str, person: str) -> str:
    subject = person.strip() or "alguien"
    place = f" en {room.strip()}" if room.strip() else ""
    if event.strip() == "person_exit_confirmed":
        return f"Aviso: {subject} ha salido{place}."
    return f"Aviso: {subject} ha entrado{place}."


def _event_notification(schedule: dict, event: dict) -> str:
    message = str(
        schedule.get("message")
        or "Ha ocurrido el evento que estabas esperando."
    ).strip()
    names = _event_people(event)
    if not names:
        return message

    identities = _join_names(names)
    enriched, substitutions = re.subn(
        r"\b(alguien|una persona|alguna persona)\b",
        identities,
        message,
        count=1,
        flags=re.IGNORECASE,
    )
    if substitutions:
        if len(names) > 1:
            enriched = re.sub(
                r"\bha (entrado|salido)\b",
                r"han \1",
                enriched,
                count=1,
                flags=re.IGNORECASE,
            )
        return enriched

    lowered = message.casefold()
    if any(name.casefold() in lowered for name in names):
        return message
    return f"{message.rstrip('.')} Identidad: {identities}."


def _event_people(event: dict) -> list[str]:
    names: list[str] = []
    for item in event.get("people") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("person") or "").strip()
        status = str(item.get("identity_status") or "known").strip().lower()
        if name and status not in {"unknown", "pending"} and name not in names:
            names.append(name)
    legacy = str(event.get("person") or "").strip()
    if legacy and legacy not in names:
        names.append(legacy)
    return names


def _join_names(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f" y {names[-1]}"
