from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from world.reminders import _event_notification


class ReminderNotificationTests(unittest.TestCase):
    def test_replaces_generic_person_with_known_identity(self):
        message = _event_notification(
            {"message": "Aviso: alguien ha entrado en el comedor."},
            {"people": [{"person": "Juancar", "identity_status": "known"}]},
        )
        self.assertEqual(message, "Aviso: Juancar ha entrado en el comedor.")

    def test_includes_multiple_known_identities(self):
        message = _event_notification(
            {"message": "Una persona ha entrado en el comedor."},
            {
                "people": [
                    {"person": "Juancar", "identity_status": "known"},
                    {"person": "Ana", "identity_status": "known"},
                ]
            },
        )
        self.assertEqual(message, "Juancar y Ana han entrado en el comedor.")

    def test_does_not_invent_identity_when_pending(self):
        message = _event_notification(
            {"message": "Aviso: alguien ha entrado en el comedor."},
            {"people": [{"person": "desconocida", "identity_status": "pending"}]},
        )
        self.assertEqual(message, "Aviso: alguien ha entrado en el comedor.")

    def test_appends_identity_to_custom_message(self):
        message = _event_notification(
            {"message": "La visita que esperabas ya está aquí."},
            {"person": "Juancar"},
        )
        self.assertEqual(
            message,
            "La visita que esperabas ya está aquí Identidad: Juancar.",
        )


if __name__ == "__main__":
    unittest.main()
