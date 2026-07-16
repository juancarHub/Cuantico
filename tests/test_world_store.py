from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from world import WorldStore


def vision_event(event_id, event, timestamp, count, people=None, person=None):
    return {"event_id": event_id, "event": event, "source": "vision_comedor",
            "room": "comedor", "timestamp": timestamp, "people_count": count,
            "people": people or [], "person": person}


class WorldStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.world = WorldStore(Path(self.temp.name) / "world.db")
        self.world.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def test_presence_and_exit_clear_current_but_preserve_last_seen(self):
        self.world.ingest(vision_event("e1", "person_presence_confirmed", "2026-07-15T20:00:00+02:00", 1, [{"person": "Juancar"}]))
        self.world.ingest(vision_event("e2", "person_exit_confirmed", "2026-07-15T20:05:00+02:00", 0, person="Juancar"))
        room, person = self.world.room("comedor"), self.world.person("Juancar")
        self.assertEqual(room["people_count"], 0)
        self.assertEqual(room["people"], [])
        self.assertIsNone(person["current_location"])
        self.assertEqual(person["last_seen_location"], "comedor")

    def test_duplicate_is_applied_once(self):
        event = vision_event("same", "person_presence_confirmed", "2026-07-15T20:00:00+02:00", 1, [{"person": "Ana"}])
        self.assertTrue(self.world.ingest(event))
        self.assertFalse(self.world.ingest(event))
        self.assertEqual(self.world.event_count(), 1)

    def test_late_event_is_audited_without_overwriting_state(self):
        self.world.ingest(vision_event("new", "person_exit_confirmed", "2026-07-15T20:10:00+02:00", 0))
        self.world.ingest(vision_event("old", "person_presence_confirmed", "2026-07-15T20:00:00+02:00", 1, [{"person": "Juancar"}]))
        self.assertEqual(self.world.event_count(), 2)
        self.assertEqual(self.world.room("comedor")["people_count"], 0)
        self.assertIsNone(self.world.person("Juancar"))

    def test_rebuild_recreates_projection(self):
        self.world.ingest(vision_event("e1", "person_presence_confirmed", "2026-07-15T20:00:00+02:00", 1, [{"person": "Juancar"}]))
        self.world.rebuild_projections()
        self.assertEqual(self.world.room("comedor")["people_count"], 1)
        self.assertEqual(self.world.person("Juancar")["current_location"], "comedor")

    def test_due_schedule_is_claimed_only_once(self):
        schedule_id = self.world.create_schedule(
            "reminder_time",
            "2026-07-15T18:00:00+00:00",
            {"message": "sacar el pollo"},
        )
        due = self.world.claim_due_schedules("2026-07-15T18:00:01+00:00")
        self.assertEqual([item["schedule_id"] for item in due], [schedule_id])
        self.assertEqual(
            self.world.claim_due_schedules("2026-07-15T18:00:02+00:00"),
            [],
        )

    def test_event_schedule_matches_room_and_expires(self):
        matched_id = self.world.create_schedule(
            "reminder_event",
            "2026-07-15T19:00:00+00:00",
            {
                "event": "person_presence_confirmed",
                "room": "comedor",
                "person": "",
                "message": "ha entrado alguien",
            },
        )
        self.world.create_schedule(
            "reminder_event",
            "2026-07-15T17:00:00+00:00",
            {
                "event": "person_presence_confirmed",
                "room": "entrada",
                "person": "",
                "message": "demasiado tarde",
            },
        )
        event = vision_event(
            "e2",
            "person_presence_confirmed",
            "2026-07-15T18:00:00+00:00",
            1,
            [{"person": "Ana"}],
        )
        matched = self.world.claim_event_schedules(
            event,
            "2026-07-15T18:00:01+00:00",
        )
        self.assertEqual([item["schedule_id"] for item in matched], [matched_id])
        self.assertEqual(self.world.schedules(), [])

    def test_cancel_schedule_by_message(self):
        self.world.create_schedule(
            "reminder_time",
            "2026-07-15T20:00:00+00:00",
            {"message": "sacar el pollo del horno"},
        )
        self.assertEqual(self.world.cancel_schedule("pollo"), 1)
        self.assertEqual(self.world.schedules(), [])


if __name__ == "__main__":
    unittest.main()
