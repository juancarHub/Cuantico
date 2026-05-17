import requests

import config
from .base import BaseSTT


class DeepgramSTT(BaseSTT):
    name = "deepgram"

    def __init__(self):
        self.api_key = config.DEEPGRAM_API_KEY
        self.model = "nova-3"
        self.language = "es"

    def transcribe(self, audio_path: str) -> str:
        url = (
            "https://api.deepgram.com/v1/listen"
            f"?model={self.model}"
            f"&language={self.language}"
            "&smart_format=true"
        )

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav",
        }

        with open(audio_path, "rb") as audio:
            response = requests.post(
                url,
                headers=headers,
                data=audio,
                timeout=20,
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Deepgram {response.status_code}: {response.text[:160]}"
            )

        return (
            response.json()["results"]
            ["channels"][0]
            ["alternatives"][0]
            ["transcript"]
            .strip()
        )
