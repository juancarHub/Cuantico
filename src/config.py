"""Carga centralizada de configuración desde .env.

Todos los módulos del proyecto importan de aquí en vez de hardcodear secretos.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# El código vive en src/, pero .env y state/ están en la raíz del repo.
_RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(_RAIZ / ".env")


def _req(clave: str) -> str:
    valor = os.getenv(clave, "").strip()
    if not valor:
        raise RuntimeError(f"Falta {clave} en .env")
    return valor


def _opt(clave: str, por_defecto: str = "") -> str:
    return os.getenv(clave, por_defecto).strip()


def _bool(clave: str, por_defecto: bool = False) -> bool:
    valor = _opt(clave, "1" if por_defecto else "0").lower()
    return valor in ("1", "true", "yes", "y", "on", "si", "sí")


def _int(clave: str, por_defecto: int) -> int:
    valor = _opt(clave, str(por_defecto))
    try:
        return int(valor)
    except ValueError as exc:
        raise RuntimeError(f"{clave} debe ser entero, recibido: {valor!r}") from exc


def _float(clave: str, por_defecto: float) -> float:
    valor = _opt(clave, str(por_defecto))
    try:
        return float(valor)
    except ValueError as exc:
        raise RuntimeError(f"{clave} debe ser numérico, recibido: {valor!r}") from exc


def _float_range(clave: str, por_defecto: float, minimo: float, maximo: float) -> float:
    valor = _float(clave, por_defecto)
    if not minimo <= valor <= maximo:
        raise RuntimeError(f"{clave} debe estar entre {minimo} y {maximo}, recibido: {valor}")
    return valor


def _choice(clave: str, por_defecto: str, opciones: tuple[str, ...]) -> str:
    valor = _opt(clave, por_defecto).lower()
    if valor not in opciones:
        raise RuntimeError(f"{clave} debe ser uno de {opciones}, recibido: {valor!r}")
    return valor


def _ruta(clave: str, por_defecto: str = "") -> str:
    """Rutas relativas se resuelven contra la raíz del repo."""
    v = _opt(clave, por_defecto)
    if not v:
        return ""
    p = Path(v)
    return str(p if p.is_absolute() else (_RAIZ / p).resolve())


# Debug / rendimiento
DEBUG_LATENCY = _bool("DEBUG_LATENCY", False)
CUANTICO_SERVER_EMBEDDED = _bool("CUANTICO_SERVER_EMBEDDED", True)

# Display / plataforma visual
DISPLAY_BACKEND = _opt("DISPLAY_BACKEND", "screen").lower()
SCREEN_DISPLAY_MODE = _opt("SCREEN_DISPLAY_MODE", "window").lower()

# Interacción tablet / entrada
INPUT_MODE = _opt("INPUT_MODE", "voice").lower()
PUSH_TO_TALK_MODE = _opt("PUSH_TO_TALK_MODE", "enter_stop").lower()
PUSH_TO_TALK_MAX_MS = _int("PUSH_TO_TALK_MAX_MS", 12000)
AUTO_STOP_SILENCE_MS = _int("AUTO_STOP_SILENCE_MS", 1400)
AUTO_STOP_MIN_VOICE_MS = _int("AUTO_STOP_MIN_VOICE_MS", 600)
AUTO_STOP_RMS_THRESHOLD = _float("AUTO_STOP_RMS_THRESHOLD", 500)

# Salida de audio
AUDIO_OUTPUT_BACKEND = _opt("AUDIO_OUTPUT_BACKEND", "auto").lower()

# LLM
LLM_PROVIDER = _opt("LLM_PROVIDER", "openai").lower()
ENABLE_LLM_STREAMING = _bool("ENABLE_LLM_STREAMING", False)
ASSISTANT_NAME = _opt("ASSISTANT_NAME", "Atlantis")
SYSTEM_PROMPT_PATH = _ruta("SYSTEM_PROMPT_PATH", "prompts/atlantis_system.txt")

OPENAI_API_KEY = _opt("OPENAI_API_KEY")
OPENAI_MODEL = _opt("OPENAI_MODEL", "gpt-4.1-mini")

GEMINI_API_KEY = _opt("GEMINI_API_KEY")
GEMINI_MODEL = _opt("GEMINI_MODEL", "gemini-3-flash-preview")

if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en .env")

if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise RuntimeError("Falta GEMINI_API_KEY en .env")

# TTS
ELEVENLABS_API_KEY = _req("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = _opt("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
OPENAI_TTS_MODEL = _opt("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_TTS_VOICE = _opt("OPENAI_TTS_VOICE", "alloy")
OPENAI_TTS_SPEED = _float_range("OPENAI_TTS_SPEED", 1.0, 0.25, 4.0)
OPENAI_TTS_FORMAT = _choice("OPENAI_TTS_FORMAT", "wav", ("mp3", "wav", "opus", "aac", "flac", "pcm"))

# STT / wake word
STT_PROVIDER = _opt("STT_PROVIDER", "deepgram").lower()
OPENAI_STT_MODEL = _opt("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
OPENAI_STT_LANGUAGE = _opt("OPENAI_STT_LANGUAGE", "es")
DEEPGRAM_API_KEY = _opt("DEEPGRAM_API_KEY")
WAKE_MODEL_PATH = _opt("WAKE_MODEL_PATH")

if STT_PROVIDER in ("deepgram", "dg") and not DEEPGRAM_API_KEY:
    raise RuntimeError("Falta DEEPGRAM_API_KEY en .env")

# Casa
GOVEE_API_KEY = _req("GOVEE_API_KEY")

# Música
SPOTIFY_CLIENT_ID = _req("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = _req("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = _opt("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

# Google OAuth (Calendar + YouTube comparten Client ID)
GOOGLE_CLIENT_SECRETS_PATH = _ruta("GOOGLE_CLIENT_SECRETS_PATH", "state/google_client.json")
GOOGLE_TOKEN_PATH = _ruta("GOOGLE_TOKEN_PATH", "state/google_token.json")
YOUTUBE_CHANNEL_ID = _opt("YOUTUBE_CHANNEL_ID")

# Directorio de estado persistente (timers, tokens, etc.)
STATE_DIR = str(_RAIZ / "state")
Path(STATE_DIR).mkdir(exist_ok=True)
