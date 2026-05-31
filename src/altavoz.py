import os
import queue
import threading
import time
from typing import Callable

import luces
from audio.output import AudioOutput
from tts import create_tts

_tts_provider = create_tts()
_audio_output = AudioOutput()


_SENTINEL = object()
_interrupt_event = threading.Event()


def interrumpir():
    """Solicita detener la respuesta hablada tras la frase en curso."""
    print("🛑 Interrupción de voz solicitada.")
    _interrupt_event.set()


def limpiar_interrupcion():
    _interrupt_event.clear()


def esta_interrumpido() -> bool:
    return _interrupt_event.is_set()


def _vaciar_cola(q: queue.Queue):
    while True:
        try:
            item = q.get_nowait()
        except queue.Empty:
            return
        try:
            if isinstance(item, str) and os.path.exists(item):
                try:
                    os.remove(item)
                except OSError:
                    pass
        finally:
            q.task_done()


def _esperar_workers(*workers: threading.Thread, timeout: float = 1.0):
    for worker in workers:
        worker.join(timeout=timeout)
        print(f"🧪 INTERRUPT: worker {worker.name} alive={worker.is_alive()}")


def _esperar_cola_o_interrupcion(q: queue.Queue) -> bool:
    while q.unfinished_tasks > 0:
        if _interrupt_event.is_set():
            return False
        time.sleep(0.02)
    return True


def _hablar_por_archivo(texto, emocion):
    print(f"🔊 TTS provider: {_tts_provider.name}")
    path = _tts_provider.generate_to_file(texto)
    try:
        if _interrupt_event.is_set():
            return
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
        if _interrupt_event.is_set():
            return
        luces.cambiar_estado(f"hablando:{emocion}")
        with open(path, "rb") as fh:
            while True:
                if _interrupt_event.is_set():
                    break
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
    limpiar_interrupcion()

    if _audio_output.use_file_backend():
        _hablar_por_archivo(texto, emocion)
    else:
        _hablar_por_tuberia_linux(texto, emocion)


def _generar_audio_frases(frases: queue.Queue, audios: queue.Queue, errores: list[BaseException]):
    print("🧪 INTERRUPT: tts_worker start")
    while True:
        frase = frases.get()
        try:
            if frase is _SENTINEL or _interrupt_event.is_set():
                print("🧪 INTERRUPT: tts_worker sentinel/interrupted -> exit")
                audios.put(_SENTINEL)
                return
            print(f"🔊 TTS provider: {_tts_provider.name}")
            path = _tts_provider.generate_to_file(frase)
            if _interrupt_event.is_set():
                print("🧪 INTERRUPT: tts_worker generated after interrupt, removing audio")
                try:
                    os.remove(path)
                except OSError:
                    pass
                audios.put(_SENTINEL)
                return
            audios.put(path)
        except BaseException as exc:
            errores.append(exc)
            audios.put(_SENTINEL)
            return
        finally:
            frases.task_done()


def _reproducir_audios(
    audios: queue.Queue,
    emocion: str,
    errores: list[BaseException],
    on_first_audio: Callable[[], None] | None = None,
):
    print("🧪 INTERRUPT: play_worker start")
    first_audio_done = False
    while True:
        path = audios.get()
        try:
            if path is _SENTINEL:
                print("🧪 INTERRUPT: play_worker sentinel -> exit")
                return
            if _interrupt_event.is_set():
                print("🧪 INTERRUPT: play_worker interrupted before play -> exit")
                return
            luces.cambiar_estado(f"hablando:{emocion}")
            if not first_audio_done:
                first_audio_done = True
                if on_first_audio:
                    on_first_audio()
            _audio_output.play_file(path)
            if _interrupt_event.is_set():
                print("🧪 INTERRUPT: play_worker interrupted after play -> exit")
                return
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


def hablar_stream(generador_texto, emocion="sarcasmo", on_first_audio: Callable[[], None] | None = None):
    print(f"🔊 [Altavoz] Streaming pipeline ({emocion})...")
    limpiar_interrupcion()

    frases: queue.Queue = queue.Queue()
    audios: queue.Queue = queue.Queue()
    errores: list[BaseException] = []

    tts_worker = threading.Thread(
        target=_generar_audio_frases,
        args=(frases, audios, errores),
        daemon=True,
        name="tts_worker",
    )
    play_worker = threading.Thread(
        target=_reproducir_audios,
        args=(audios, emocion, errores, on_first_audio),
        daemon=True,
        name="play_worker",
    )
    tts_worker.start()
    play_worker.start()

    buffer = ""
    try:
        for chunk in generador_texto:
            if errores or _interrupt_event.is_set():
                print("🧪 INTERRUPT: main stream loop break")
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
                if frase and not _interrupt_event.is_set():
                    frases.put(frase)

        if buffer.strip() and not errores and not _interrupt_event.is_set():
            frases.put(buffer.strip())
    finally:
        print(f"🧪 INTERRUPT: entrar finally hablar_stream interrupted={_interrupt_event.is_set()}")
        frases.put(_SENTINEL)
        if not _esperar_cola_o_interrupcion(frases):
            print("🧪 INTERRUPT: interrupción mientras esperaba frases")
            _vaciar_cola(frases)
            _vaciar_cola(audios)
            audios.put(_SENTINEL)
            _esperar_workers(tts_worker, play_worker, timeout=1.0)
            print("🧪 INTERRUPT: saliendo hablar_stream")
            return

        if not _esperar_cola_o_interrupcion(audios):
            print("🧪 INTERRUPT: interrupción mientras esperaba audios")
            _vaciar_cola(audios)
            audios.put(_SENTINEL)
            _esperar_workers(tts_worker, play_worker, timeout=1.0)
            print("🧪 INTERRUPT: saliendo hablar_stream")
            return

        _esperar_workers(tts_worker, play_worker, timeout=1.0)
        print("🧪 INTERRUPT: saliendo hablar_stream")

    if errores:
        raise errores[0]
