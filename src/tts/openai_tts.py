import tempfile

from openai import OpenAI

import config
from .base import BaseTTS


class OpenAITTS(BaseTTS):
    name = "openai"

    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_TTS_MODEL
        self.voice = config.OPENAI_TTS_VOICE
        self.speed = config.OPENAI_TTS_SPEED

    def generate_to_file(self, text: str) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            path = tmp.name

        with self.client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=self.voice,
            input=text,
            speed=self.speed,
            response_format="mp3",
        ) as response:
            response.stream_to_file(path)

        return path
