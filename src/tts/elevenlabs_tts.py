import tempfile

import requests

import config
from .base import BaseTTS


class ElevenLabsTTS(BaseTTS):
    name = "elevenlabs"

    def __init__(self):
        self.api_key = config.ELEVENLABS_API_KEY
        self.voice_id = config.ELEVENLABS_VOICE_ID
        self.model = "eleven_turbo_v2_5"

    def generate_to_file(self, text: str) -> str:
        url = (
            f"https://api.elevenlabs.io/v1/text-to-speech/"
            f"{self.voice_id}?output_format=mp3_22050_32"
        )

        payload = {
            "text": text,
            "model_id": self.model,
            "language_code": "es",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=45)
        if response.status_code != 200:
            raise RuntimeError(
                f"ElevenLabs {response.status_code}: {response.text[:160]}"
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(response.content)
            return tmp.name
