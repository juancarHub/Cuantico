import os
import queue
import threading

import luces
from audio.output import AudioOutput
from tts import create_tts

_tts_provider = create_tts()
_audio_output = AudioOutput()


_SENTINEL = object()


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


def _generar_audio_frases(frases: queue.Queue, audios: queue.Queue, errores: list[BaseException]):
    while True:
        frase = frases.get()
        try:
            if frase is _SENTINEL:
                audios.put(_SENTINEL)
                return
            print(f"🔊 TTS provider: {_tts_provider.name}")
            path = _tts_provider.generate_to_file(frase)
            audios.put(path)
        except BaseException as exc:
            errores.append(exc)
            audios.put(_SENTINEL)
            return
        finally:
            frases.task_done()


def _reproducir_audios(audios: queue.Queue, emocion: str, errores: list[BaseException]):
    while True:
        path = audios.get()
        try:
            if path is _SENTINEL:
                return
            luces.cambiar_estado(f"hablando:{emocion}")
            _audio_output.play_file(path)
        except BaseException as exc:
            errores.append(exc)
            return
        finally:
            if path is not _SENTINEL:
                try:
                    os.remove(path)
                except OSError:
                    pass
            audios.task_done()


def hablar_stream(generador_texto, emocion="sarcasmo"):
    print(f"🔊 [Altavoz] Streaming pipeline ({emocion})...")

    frases: queue.Queue = queue.Queue()
    audios: queue.Queue = queue.Queue()
    errores: list[BaseException] = []

    tts_worker = threading.Thread(
        target=_generar_audio_frases,
        args=(frases, audios, errores),
        daemon=True,
    )
    play_worker = threading.Thread(
        target=_reproducir_audios,
        args=(audios, emocion, errores),
        daemon=True,
    )
    tts_worker.start()
    play_worker.start()

    buffer = ""
    try:
        for chunk in generador_texto:
            if errores:
                break
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
                    frases.put(frase)

        if buffer.strip() and not errores:
            frases.put(buffer.strip())
    finally:
        frases.put(_SENTINEL)
        frases.join()
        audios.join()
        tts_worker.join(timeout=1.0)
        play_worker.join(timeout=1.0)

    if errores:
        raise errores[0]
