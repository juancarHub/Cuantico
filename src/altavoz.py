import os
import platform
import subprocess

import luces
from tts import create_tts

_tts_provider = create_tts()


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
    """Pipeline Linux/Raspberry: MP3 → sox → aplay."""
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


def _reproducir_archivo(path):
    try:
        from playsound import playsound
    except Exception as exc:
        raise RuntimeError(
            "Falta playsound. Instala con: pip install playsound==1.2.2"
        ) from exc

    playsound(path)


def _hablar_por_archivo(texto):
    print(f"🔊 TTS provider: {_tts_provider.name}")
    path = _tts_provider.generate_to_file(texto)
    try:
        _reproducir_archivo(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _hablar_por_tuberia_linux(texto):
    path = _tts_provider.generate_to_file(texto)
    proceso = _lanzar_mpg123()
    try:
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(2048)
                if not chunk:
                    break
                proceso.stdin.write(chunk)
                proceso.stdin.flush()
    finally:
        try:
            proceso.stdin.close()
        except Exception:
            pass
        proceso.wait()
        try:
            os.remove(path)
        except OSError:
            pass


def _encontrar_corte(buffer):
    candidatos = []
    for p in [". ", "! ", "? ", ".\n", "!\n", "?\n", "\n"]:
        i = buffer.find(p)
        if i != -1:
            candidatos.append(i + len(p) - 1)
    return min(candidatos) if candidatos else -1


def hablar(texto, emocion):
    luces.cambiar_estado(emocion)
    print(f"🔊 [Altavoz] Escupiendo audio ({emocion})...")

    if _usar_backend_archivo():
        _hablar_por_archivo(texto)
    else:
        _hablar_por_tuberia_linux(texto)


def hablar_stream(generador_texto, emocion="sarcasmo"):
    luces.cambiar_estado(emocion)
    print(f"🔊 [Altavoz] Streaming paralelo ({emocion})...")

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
                hablar(frase, emocion)

    if buffer.strip():
        hablar(buffer.strip(), emocion)
