import os
import time

import numpy as np

import config
from audio.input import AudioInput, SAMPLE_RATE, VAD_FRAME, VAD_FRAME_MS
from stt import create_stt

WAKE_MODEL = config.WAKE_MODEL_PATH
WAKE_THRESHOLD = 0.3
SILENCE_MS_TO_STOP = 400
MIN_VOICE_MS = 300
MAX_UTTERANCE_MS = 8000

_audio_input = AudioInput()
_stt_provider = create_stt()
_oww = None
_vad = None


def inicializar(use_wake_word=True):
    global _oww, _vad
    _audio_input.inicializar()

    if use_wake_word:
        import webrtcvad
        from openwakeword.model import Model

        _vad = webrtcvad.Vad(2)
        print("🦻 Cargando openWakeWord...")
        _oww = Model(wakeword_models=[WAKE_MODEL], inference_framework="onnx")
        print("✅ Micro en modo radar: escuchando wake word.")
    else:
        print("✅ Micro en modo push-to-talk/manual sin VAD ni wake word.")


def _esperar_wake():
    if _oww is None:
        return
    _oww.reset()
    ultimo_log = 0.0
    while True:
        raw = _audio_input.leer_raw(1280)
        audio = np.frombuffer(raw, dtype=np.int16)
        scores = _oww.predict(audio)
        mejor = max(scores.values())
        if mejor > 0.05 and abs(mejor - ultimo_log) > 0.02:
            print(f"   🔍 score wake={mejor:.3f} (threshold {WAKE_THRESHOLD})")
            ultimo_log = mejor
        if mejor > WAKE_THRESHOLD:
            return


def _esperar_voz(timeout_ms):
    if _vad is None:
        return None
    ms_esperados = 0
    while ms_esperados < timeout_ms:
        frame = _audio_input.leer_raw(VAD_FRAME)
        if _vad.is_speech(frame, SAMPLE_RATE):
            return frame
        ms_esperados += VAD_FRAME_MS
    return None


def _grabar_desde(frame_inicial=b""):
    if _vad is None:
        return _audio_input.grabar_manual()

    buffer_audio = bytearray(frame_inicial)
    silencio_ms = 0
    voz_ms = VAD_FRAME_MS if frame_inicial else 0
    inicio = time.time()

    while True:
        frame = _audio_input.leer_raw(VAD_FRAME)
        buffer_audio += frame

        if _vad.is_speech(frame, SAMPLE_RATE):
            voz_ms += VAD_FRAME_MS
            silencio_ms = 0
        else:
            silencio_ms += VAD_FRAME_MS

        if voz_ms >= MIN_VOICE_MS and silencio_ms >= SILENCE_MS_TO_STOP:
            break
        if (time.time() - inicio) * 1000 > MAX_UTTERANCE_MS:
            break

    return _audio_input.guardar_wav(buffer_audio)


def _transcribir(path):
    print(f"🧠 [STT:{_stt_provider.name}] Analizando...")
    try:
        return _stt_provider.transcribe(path)
    except Exception as e:
        print(f"⚠️ Error STT ({_stt_provider.name}): {e}")
        return ""
    finally:
        if os.path.exists(path):
            os.remove(path)


def escuchar():
    print("💤 En reposo. Di la wake word para despertarme...")
    _esperar_wake()
    print("🎤 [Wake] ¡Despierto! Escuchando tu petición...")
    wav = _grabar_desde()
    return _transcribir(wav)


def escuchar_push_to_talk():
    input("\nPulsa ENTER para empezar a grabar... ")
    wav = _audio_input.grabar_manual()
    return _transcribir(wav)


def escuchar_seguimiento(timeout_ms=8000):
    if _vad is None:
        return escuchar_push_to_talk()

    print(f"👂 ¿Algo más? ({timeout_ms//1000}s)...")
    frame = _esperar_voz(timeout_ms)
    if frame is None:
        print("⌛ Silencio. Volviendo al modo radar.")
        return None
    print("🎤 Voz captada, grabando...")
    wav = _grabar_desde(frame)
    return _transcribir(wav)


def cerrar():
    _audio_input.cerrar()
