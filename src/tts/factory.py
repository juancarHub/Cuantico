import os

from .elevenlabs_tts import ElevenLabsTTS
from .openai_tts import OpenAITTS


TTS_PROVIDER = os.getenv("TTS_PROVIDER", "elevenlabs").lower()


def create_tts():
    if TTS_PROVIDER == "openai":
        return OpenAITTS()

    if TTS_PROVIDER in ("eleven", "elevenlabs", "11labs"):
        return ElevenLabsTTS()

    raise RuntimeError(f"Proveedor TTS no soportado: {TTS_PROVIDER}")
