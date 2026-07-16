from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


VISION_EVENTS = {"person_presence_confirmed", "person_identity_pending", "person_identified", "person_exit_confirmed"}


class WorldStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS world_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    room TEXT,
                    occurred_at TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS world_rooms (
                    room_id TEXT PRIMARY KEY,
                    occupancy INTEGER NOT NULL DEFAULT 0,
                    observed_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    last_event_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS world_room_people (
                    room_id TEXT NOT NULL,
                    person_name TEXT NOT NULL,
                    identity_status TEXT NOT NULL DEFAULT 'known',
                    observed_at TEXT NOT NULL,
                    PRIMARY KEY (room_id, person_name),
                    FOREIGN KEY (room_id) REFERENCES world_rooms(room_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS world_people (
                    person_name TEXT PRIMARY KEY,
                    current_location TEXT,
                    last_seen_location TEXT,
                    last_seen_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL
                );
                CREATE TABLE IF NOT EXISTS world_actions (
                    action_id TEXT PRIMARY KEY, action_type TEXT NOT NULL, target TEXT,
                    status TEXT NOT NULL, reason TEXT, requested_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}', result_json TEXT
                );
                CREATE TABLE IF NOT EXISTS world_schedules (
                    schedule_id TEXT PRIMARY KEY, action_type TEXT NOT NULL, execute_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'scheduled', payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS world_rules (
                    rule_id TEXT PRIMARY KEY, description TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
                    rule_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, confirmed_by TEXT
                );
                CREATE TABLE IF NOT EXISTS assistant_runtime (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1), status TEXT NOT NULL,
                    current_activity TEXT, last_activity TEXT, updated_at TEXT NOT NULL
                );
                """
            )
            db.execute(
                "INSERT OR IGNORE INTO assistant_runtime (singleton, status, updated_at) VALUES (1, 'idle', ?)",
                (_now_utc(),),
            )

    def ingest(self, event: dict[str, Any]) -> bool:
        payload = dict(event)
        event_type = str(payload.get("event") or "unknown")
        source = str(payload.get("source") or "unknown")
        room = _clean(payload.get("room"))
        received_at = _now_utc()
        occurred_at = _timestamp(payload.get("timestamp"), received_at)
        event_id = _event_id(payload, source, event_type, occurred_at)
        payload["event_id"] = event_id
        with self._lock, self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            inserted = db.execute(
                """INSERT OR IGNORE INTO world_events
                (event_id,event_type,source,room,occurred_at,received_at,payload_json)
                VALUES (?,?,?,?,?,?,?)""",
                (event_id, event_type, source, room, occurred_at, received_at,
                 json.dumps(payload, ensure_ascii=False, sort_keys=True)),
            )
            if inserted.rowcount == 0:
                db.rollback()
                return False
            try:
                self._apply_projection(db, payload, occurred_at)
                db.commit()
            except Exception:
                db.rollback()
                raise
            return True

    def _apply_projection(self, db: sqlite3.Connection, event: dict[str, Any], observed_at: str) -> None:
        if event.get("event") not in VISION_EVENTS:
            return
        room = _clean(event.get("room")) or str(event.get("source") or "desconocida")
        source = str(event.get("source") or "unknown")
        current = db.execute("SELECT observed_at FROM world_rooms WHERE room_id=?", (room,)).fetchone()
        if current and current[0] > observed_at:
            return
        old_names = {r[0] for r in db.execute("SELECT person_name FROM world_room_people WHERE room_id=?", (room,))}
        people = _known_people(event)
        new_names = {p["person"] for p in people}
        occupancy = max(0, int(event.get("people_count") or 0))
        db.execute(
            """INSERT INTO world_rooms(room_id,occupancy,observed_at,source,last_event_id)
            VALUES(?,?,?,?,?) ON CONFLICT(room_id) DO UPDATE SET
            occupancy=excluded.occupancy,observed_at=excluded.observed_at,
            source=excluded.source,last_event_id=excluded.last_event_id""",
            (room, occupancy, observed_at, source, str(event["event_id"])),
        )
        db.execute("DELETE FROM world_room_people WHERE room_id=?", (room,))
        for person in people:
            name = person["person"]
            db.execute(
                "INSERT INTO world_room_people(room_id,person_name,identity_status,observed_at) VALUES(?,?,?,?)",
                (room, name, person.get("identity_status", "known"), observed_at),
            )
            db.execute("DELETE FROM world_room_people WHERE person_name=? AND room_id<>?", (name, room))
            self._upsert_person(db, name, room, observed_at, source)
        removed = old_names - new_names
        trigger = _clean(event.get("person"))
        if event.get("event") == "person_exit_confirmed" and trigger:
            removed.add(trigger)
        for name in removed:
            db.execute(
                "UPDATE world_people SET current_location=NULL WHERE person_name=? AND current_location=? AND last_seen_at<=?",
                (name, room, observed_at),
            )

    def _upsert_person(self, db: sqlite3.Connection, name: str, room: str, observed_at: str, source: str) -> None:
        db.execute(
            """INSERT INTO world_people(person_name,current_location,last_seen_location,last_seen_at,source)
            VALUES(?,?,?,?,?) ON CONFLICT(person_name) DO UPDATE SET
            current_location=CASE WHEN excluded.last_seen_at>=world_people.last_seen_at THEN excluded.current_location ELSE world_people.current_location END,
            last_seen_location=CASE WHEN excluded.last_seen_at>=world_people.last_seen_at THEN excluded.last_seen_location ELSE world_people.last_seen_location END,
            last_seen_at=MAX(world_people.last_seen_at,excluded.last_seen_at),
            source=CASE WHEN excluded.last_seen_at>=world_people.last_seen_at THEN excluded.source ELSE world_people.source END""",
            (name, room, room, observed_at, source),
        )

    def room(self, name: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as db:
            row = db.execute("SELECT room_id,occupancy,observed_at,source,last_event_id FROM world_rooms WHERE LOWER(room_id)=LOWER(?)", (name.strip(),)).fetchone()
            if not row:
                return None
            people = [{"person": p[0], "identity_status": p[1]} for p in db.execute(
                "SELECT person_name,identity_status FROM world_room_people WHERE room_id=? ORDER BY person_name", (row[0],))]
            return {"room": row[0], "people_count": row[1], "people": people,
                    "observed_at": row[2], "source": row[3], "last_event_id": row[4]}

    def person(self, name: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as db:
            row = db.execute("""SELECT person_name,current_location,last_seen_location,last_seen_at,source,confidence
                FROM world_people WHERE LOWER(person_name)=LOWER(?)""", (name.strip(),)).fetchone()
            return None if not row else {"person": row[0], "current_location": row[1],
                "last_seen_location": row[2], "last_seen_at": row[3], "source": row[4], "confidence": row[5]}

    def snapshot(self) -> dict[str, Any]:
        with self._lock, self._connection() as db:
            room_names = [r[0] for r in db.execute("SELECT room_id FROM world_rooms ORDER BY room_id")]
            person_names = [r[0] for r in db.execute("SELECT person_name FROM world_people ORDER BY person_name")]
            runtime = db.execute("SELECT status,current_activity,last_activity,updated_at FROM assistant_runtime WHERE singleton=1").fetchone()
        return {"rooms": [self.room(n) for n in room_names], "people": [self.person(n) for n in person_names],
                "runtime": {"status": runtime[0], "current_activity": runtime[1], "last_activity": runtime[2], "updated_at": runtime[3]} if runtime else None}

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connection() as db:
            rows = db.execute("SELECT payload_json FROM world_events ORDER BY sequence DESC LIMIT ?", (max(1, min(limit, 200)),)).fetchall()
        return [json.loads(r[0]) for r in reversed(rows)]

    def event_count(self) -> int:
        with self._lock, self._connection() as db:
            return int(db.execute("SELECT COUNT(*) FROM world_events").fetchone()[0])

    def create_schedule(
        self,
        action_type: str,
        execute_at: str,
        payload: dict[str, Any],
    ) -> str:
        schedule_id = secrets.token_hex(4)
        with self._lock, self._connection() as db:
            db.execute(
                """INSERT INTO world_schedules
                (schedule_id,action_type,execute_at,status,payload_json,created_at)
                VALUES(?,?,?,'scheduled',?,?)""",
                (
                    schedule_id,
                    action_type,
                    _timestamp(execute_at, _now_utc()),
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    _now_utc(),
                ),
            )
            db.commit()
        return schedule_id

    def schedules(self, status: str = "scheduled") -> list[dict[str, Any]]:
        with self._lock, self._connection() as db:
            rows = db.execute(
                """SELECT schedule_id,action_type,execute_at,status,payload_json,created_at
                FROM world_schedules WHERE status=? ORDER BY execute_at,created_at""",
                (status,),
            ).fetchall()
        return [
            {
                "schedule_id": row[0],
                "action_type": row[1],
                "execute_at": row[2],
                "status": row[3],
                "payload": json.loads(row[4]),
                "created_at": row[5],
            }
            for row in rows
        ]

    def cancel_schedule(self, id_or_text: str) -> int:
        needle = id_or_text.strip().lower()
        if not needle:
            return 0
        with self._lock, self._connection() as db:
            rows = db.execute(
                """SELECT schedule_id,payload_json FROM world_schedules
                WHERE status='scheduled'"""
            ).fetchall()
            ids = [
                row[0]
                for row in rows
                if row[0].lower() == needle or needle in row[1].lower()
            ]
            if ids:
                db.executemany(
                    "UPDATE world_schedules SET status='cancelled' WHERE schedule_id=?",
                    [(schedule_id,) for schedule_id in ids],
                )
                db.commit()
            return len(ids)

    def claim_due_schedules(self, now: str | None = None) -> list[dict[str, Any]]:
        now_utc = _timestamp(now, _now_utc()) if now else _now_utc()
        with self._lock, self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                """UPDATE world_schedules SET status='expired'
                WHERE status='scheduled' AND action_type='reminder_event'
                AND execute_at<?""",
                (now_utc,),
            )
            rows = db.execute(
                """SELECT schedule_id,action_type,execute_at,payload_json
                FROM world_schedules
                WHERE status='scheduled' AND action_type='reminder_time' AND execute_at<=?
                ORDER BY execute_at""",
                (now_utc,),
            ).fetchall()
            for row in rows:
                payload = json.loads(row[3])
                if payload.get("recurrence") == "daily":
                    next_at = _next_daily_occurrence(payload, now_utc)
                    db.execute(
                        "UPDATE world_schedules SET execute_at=? WHERE schedule_id=?",
                        (next_at, row[0]),
                    )
                else:
                    db.execute(
                        "UPDATE world_schedules SET status='triggered' WHERE schedule_id=?",
                        (row[0],),
                    )
            db.commit()
        return [
            {
                "schedule_id": row[0],
                "action_type": row[1],
                "execute_at": row[2],
                "payload": json.loads(row[3]),
            }
            for row in rows
        ]

    def claim_event_schedules(
        self,
        event: dict[str, Any],
        now: str | None = None,
    ) -> list[dict[str, Any]]:
        now_utc = _timestamp(now, _now_utc()) if now else _now_utc()
        matched: list[tuple] = []
        expired: list[str] = []
        with self._lock, self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                """SELECT schedule_id,action_type,execute_at,payload_json
                FROM world_schedules
                WHERE status='scheduled' AND action_type='reminder_event'"""
            ).fetchall()
            for row in rows:
                payload = json.loads(row[3])
                if row[2] < now_utc:
                    expired.append(row[0])
                elif _schedule_matches_event(payload, event):
                    matched.append(row)
            if expired:
                db.executemany(
                    "UPDATE world_schedules SET status='expired' WHERE schedule_id=?",
                    [(schedule_id,) for schedule_id in expired],
                )
            if matched:
                for row in matched:
                    payload = json.loads(row[3])
                    if not payload.get("repeat"):
                        db.execute(
                            "UPDATE world_schedules SET status='triggered' WHERE schedule_id=?",
                            (row[0],),
                        )
            db.commit()
        return [
            {
                "schedule_id": row[0],
                "action_type": row[1],
                "execute_at": row[2],
                "payload": json.loads(row[3]),
            }
            for row in matched
        ]

    def update_runtime(self, status: str, activity: str | None = None) -> None:
        with self._lock, self._connection() as db:
            db.execute(
                """UPDATE assistant_runtime SET
                last_activity=CASE WHEN current_activity IS NOT NULL THEN current_activity ELSE last_activity END,
                status=?, current_activity=?, updated_at=? WHERE singleton=1""",
                (status, activity, _now_utc()),
            )
            db.commit()

    def format_for_prompt(self) -> str:
        rooms = self.snapshot()["rooms"]
        if not rooms:
            return ""
        lines = ["CUANTICO WORLD - ESTADO ACTUAL:"]
        for room in rooms:
            names = [p["person"] for p in room["people"]]
            lines.append(f"- {room['room']}: {room['people_count']} persona(s); {', '.join(names) if names else 'sin identidades confirmadas'}; observado {room['observed_at']}")
        return "\n".join(lines)

    def rebuild_projections(self) -> None:
        with self._lock, self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            events = db.execute("SELECT payload_json,occurred_at FROM world_events ORDER BY sequence").fetchall()
            db.execute("DELETE FROM world_room_people"); db.execute("DELETE FROM world_rooms"); db.execute("DELETE FROM world_people")
            for payload, occurred_at in events:
                self._apply_projection(db, json.loads(payload), occurred_at)
            db.commit()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.path), timeout=10.0)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @contextmanager
    def _connection(self):
        db = self._connect()
        try:
            yield db
        finally:
            db.close()


def _known_people(event: dict[str, Any]) -> list[dict[str, str]]:
    result = []
    for item in event.get("people") or []:
        if isinstance(item, dict) and _clean(item.get("person")):
            result.append({"person": _clean(item["person"]), "identity_status": str(item.get("identity_status") or "known")})
    legacy = _clean(event.get("person")) if event.get("event") != "person_exit_confirmed" else None
    if legacy and all(p["person"] != legacy for p in result):
        result.append({"person": legacy, "identity_status": "known"})
    return result


def _clean(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _timestamp(value: Any, fallback: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None: parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        return fallback


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_id(payload: dict[str, Any], source: str, event_type: str, occurred_at: str) -> str:
    if _clean(payload.get("event_id")): return str(payload["event_id"]).strip()
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return f"{source}:{event_type}:{occurred_at}:{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"


def _schedule_matches_event(schedule: dict[str, Any], event: dict[str, Any]) -> bool:
    expected_event = _clean(schedule.get("event"))
    expected_room = _clean(schedule.get("room"))
    expected_person = _clean(schedule.get("person"))
    if expected_event and str(event.get("event") or "").lower() != expected_event.lower():
        return False
    if expected_room and str(event.get("room") or "").lower() != expected_room.lower():
        return False
    if expected_person:
        names = {
            str(item.get("person") or "").lower()
            for item in event.get("people") or []
            if isinstance(item, dict)
        }
        legacy = _clean(event.get("person"))
        if legacy:
            names.add(legacy.lower())
        if expected_person.lower() not in names:
            return False
    return True


def _next_daily_occurrence(payload: dict[str, Any], after_utc: str) -> str:
    timezone_name = str(payload.get("timezone") or "Europe/Madrid")
    local_zone = ZoneInfo(timezone_name)
    after = datetime.fromisoformat(after_utc).astimezone(local_zone)
    hour = int(payload.get("hour", 0))
    minute = int(payload.get("minute", 0))
    candidate = after.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= after:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc).isoformat()
