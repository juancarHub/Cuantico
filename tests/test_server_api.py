from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

_IMPORT_TEMP = tempfile.TemporaryDirectory()
os.environ["CUANTICO_WORLD_DB"] = str(Path(_IMPORT_TEMP.name) / "import-world.db")

import server.app as server_app
from server.app import app, set_event_handler
from world import WorldStore


class ServerApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        server_app.world = WorldStore(Path(self.temp.name) / "server-world.db")
        server_app.world.initialize()
        self.environment = patch.dict(
            os.environ,
            {
                "CUANTICO_API_TOKEN": "api-secret",
                "CUANTICO_NODE_TOKENS": "vision_entrada:node-secret",
            },
        )
        self.environment.start()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        set_event_handler(None)
        self.client.close()
        self.environment.stop()
        self.temp.cleanup()

    def test_health_is_public(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_events_require_token_and_are_accepted(self):
        payload = {
            "event": "person_presence_confirmed",
            "event_id": "vision_entrada:event_1",
            "source": "vision_entrada",
            "room": "entrada",
            "people_count": 1,
        }

        unauthorized = self.client.post("/api/v1/events", json=payload)
        accepted = self.client.post(
            "/api/v1/events",
            json=payload,
            headers={"Authorization": "Bearer api-secret"},
        )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["event_id"], "vision_entrada:event_1")

    def test_events_accept_token_specific_to_node(self):
        response = self.client.post(
            "/api/v1/events",
            json={"event": "test", "source": "vision_entrada"},
            headers={"Authorization": "Bearer node-secret"},
        )

        self.assertEqual(response.status_code, 200)

    def test_accepted_event_is_forwarded_to_integrated_handler(self):
        received = []
        set_event_handler(received.append)

        response = self.client.post(
            "/api/v1/events",
            json={"event": "person_identified", "source": "vision_entrada", "person": "Ana"},
            headers={"Authorization": "Bearer node-secret"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(received[0]["event"], "person_identified")
        self.assertEqual(received[0]["person"], "Ana")

    def test_speak_command_reaches_connected_node(self):
        with self.client.websocket_connect(
            "/api/v1/nodes/vision_entrada/stream?token=node-secret"
        ) as websocket:
            response = self.client.post(
                "/api/v1/nodes/vision_entrada/speak",
                json={"event_id": "speak_1", "text": "Hola desde Cuantico"},
                headers={"Authorization": "Bearer api-secret"},
            )
            command = websocket.receive_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["connected"])
        self.assertEqual(command["event"], "node_speak")
        self.assertEqual(command["target_source"], "vision_entrada")
        self.assertEqual(command["text"], "Hola desde Cuantico")


if __name__ == "__main__":
    unittest.main()
