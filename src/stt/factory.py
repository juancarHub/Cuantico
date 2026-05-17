import config

from .deepgram_stt import DeepgramSTT
from .openai_stt import OpenAISTT


STT_PROVIDER = config.STT_PROVIDER


def create_stt():
    if STT_PROVIDER == "openai":
        return OpenAISTT()

    if STT_PROVIDER in ("deepgram", "dg"):
        return DeepgramSTT()

    raise RuntimeError(f"Proveedor STT no soportado: {STT_PROVIDER}")
