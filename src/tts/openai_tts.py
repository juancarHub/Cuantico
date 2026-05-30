import tempfile
import time

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
        self.format = config.OPENAI_TTS_FORMAT

    def generate_to_file(self, text: str) -> str:
        t0 = time.perf_counter()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{self.format}") as tmp:
            path = tmp.name

        with self.client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=self.voice,
            input=text,
            speed=self.speed,
            response_format=self.format,
        ) as response:
            response.stream_to_file(path)

        if config.DEBUG_LATENCY:
            print(f"⏱️ TTS(OpenAI): {time.perf_counter() - t0:.2f}s")

        return path
