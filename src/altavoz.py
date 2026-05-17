import os
import platform
import subprocess
import tempfile

import requests

import config
import luces

ELEVENLABS_API_KEY = config.ELEVENLABS_API_KEY
VOICE_ID = config.ELEVENLABS_VOICE_ID
TTS_MODEL = "eleven_turbo_v2_5"  # ~250ms TTFB, calidad cercana al multilingual


def _backend_audio():
    return os.getenv("AUDIO_OUTPUT_BACKEND", "auto").lower()


def _usar_backend_archivo():
    backend = _backend_audio()
    if backend in ("file", "windows", "playsound"):
        return True
    if backend in ("linux", "aplay", "sox"):
        return False
    return platform.system().lower().startswith("win")


def _lanzar_mpg123():
    """
    Pipeline Linux/Raspberry: MP3 → sox → aplay.
    Se mantiene para la Pi, pero en Windows usamos reproducción por fichero.
    """
    sox_proc = subprocess.Popen(
        ["sox", "-q", "-t", "mp3", "-", "-t", "wav", "-",
         "highpass", "300",
         "bass", "-4",
         "treble", "+2",
         "gain", "-n", "-5"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    aplay_proc = subprocess.Popen(
        ["aplay", "-q", "-D", "default"],
        stdin=sox_proc.stdout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sox_proc.stdout.close()

    class Pipeline:
        def __init__(self, a, b):
            self._a = a
            self._b = b
            self.stdin = a.stdin

        def wait(self):
            self._a.wait()
            self._b.wait()

    return Pipeline(sox_proc, aplay_proc)


def _payload_tts(texto):
    return {
        "text": texto,
        "model_id": TTS_MODEL,
        "language_code": "es",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }


def _headers_tts():
    return {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }


def _tts_a_tuberia(texto, stdin):
    """Pide audio a ElevenLabs en streaming y escribe bytes directos al pipeline Linux."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream?output_format=mp3_22050_32"
    r = requests.post(url, json=_payload_tts(texto), headers=_headers_tts(), stream=True, timeout=30)
    if r.status_code != 200:
        print(f"⚠️ ElevenLabs {r.status_code}: {r.text[:120]}")
        return
    for chunk in r.iter_content(chunk_size=2048):
        if chunk:
            try:
                stdin.write(chunk)
                stdin.flush()
            except BrokenPipeError:
                return


def _tts_a_mp3_file(texto):
    """Genera un MP3 temporal multiplataforma desde ElevenLabs."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_22050_32"
    r = requests.post(url, json=_payload_tts(texto), headers=_headers_tts(), timeout=45)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:160]}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(r.content)
        return tmp.name


def _reproducir_archivo(path):
    """Reproduce un fichero de audio en Windows/macOS/Linux usando playsound."""
    try:
        from playsound import playsound
    except Exception as exc:
        raise RuntimeError(
            "Falta playsound. Instala con: pip install playsound==1.2.2"
        ) from exc

    playsound(path)


def _hablar_por_archivo(texto):
    path = _tts_a_mp3_file(texto)
    try:
        _reproducir_archivo(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _encontrar_corte(buffer):
    """Devuelve índice del final de la primera frase, o -1 si no hay."""
    candidatos = []
    for p in [". ", "! ", "? ", ".\n", "!\n", "?\n", "\n"]:
        i = buffer.find(p)
        if i != -1:
            candidatos.append(i + len(p) - 1)
    return min(candidatos) if candidatos else -1


def hablar(texto, emocion):
    """Reproduce un texto completo."""
    luces.cambiar_estado(emocion)
    print(f"🔊 [Altavoz] Escupiendo audio ({emocion})...")

    if _usar_backend_archivo():
        _hablar_por_archivo(texto)
        return

    proceso = _lanzar_mpg123()
    try:
        _tts_a_tuberia(texto, proceso.stdin)
    finally:
        try:
            proceso.stdin.close()
        except Exception:
            pass
        proceso.wait()


def hablar_stream(generador_texto, emocion="sarcasmo"):
    """
    Recibe un generador de strings y habla por frases.
    En Windows se reproduce frase a frase por ficheros temporales.
    En Raspberry conserva el pipeline streaming sox/aplay.
    """
    luces.cambiar_estado(emocion)
    print(f"🔊 [Altavoz] Streaming paralelo ({emocion})...")

    if _usar_backend_archivo():
        buffer = ""
        for chunk in generador_texto:
            if not chunk:
                continue
            buffer += chunk
            while True:
                idx = _encontrar_corte(buffer)
                if idx == -1:
                    break
                frase = buffer[: idx + 1].strip()
                buffer = buffer[idx + 1:]
                if frase:
                    _hablar_por_archivo(frase)
        if buffer.strip():
            _hablar_por_archivo(buffer.strip())
        return

    proceso = _lanzar_mpg123()
    buffer = ""
    try:
        for chunk in generador_texto:
            if not chunk:
                continue
            buffer += chunk
            while True:
                idx = _encontrar_corte(buffer)
                if idx == -1:
                    break
                frase = buffer[: idx + 1].strip()
                buffer = buffer[idx + 1:]
                if frase:
                    _tts_a_tuberia(frase, proceso.stdin)
        if buffer.strip():
            _tts_a_tuberia(buffer.strip(), proceso.stdin)
    finally:
        try:
            proceso.stdin.close()
        except Exception:
            pass
        proceso.wait()
