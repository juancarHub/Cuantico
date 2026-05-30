import os

import luces
from audio.output import AudioOutput
from tts import create_tts

_tts_provider = create_tts()
_audio_output = AudioOutput()


def _hablar_por_archivo(texto, emocion):
    print(f"🔊 TTS provider: {_tts_provider.name}")
    path = _tts_provider.generate_to_file(texto)
    try:
        luces.cambiar_estado(f"hablando:{emocion}")
        _audio_output.play_file(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _hablar_por_tuberia_linux(texto, emocion):
    path = _tts_provider.generate_to_file(texto)
    proceso = _audio_output.create_linux_pipeline()
    try:
        luces.cambiar_estado(f"hablando:{emocion}")
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
    print(f"🔊 [Altavoz] Preparando audio ({emocion})...")

    if _audio_output.use_file_backend():
        _hablar_por_archivo(texto, emocion)
    else:
        _hablar_por_tuberia_linux(texto, emocion)


def hablar_stream(generador_texto, emocion="sarcasmo"):
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
