from openai import OpenAI

import config
from .base import BaseSTT


class OpenAISTT(BaseSTT):
    name = "openai"

    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_STT_MODEL
        self.language = config.OPENAI_STT_LANGUAGE

    def transcribe(self, audio_path: str) -> str:
        with open(audio_path, "rb") as audio:
            result = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio,
                language=self.language,
            )

        return (result.text or "").strip()
