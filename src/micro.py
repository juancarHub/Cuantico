import os
import tempfile
import threading
import time
import wave

import numpy as np
import pyaudio
import requests

import config
import luces

DEEPGRAM_API_KEY = config.DEEPGRAM_API_KEY
WAKE_MODEL = config.WAKE_MODEL_PATH

SAMPLE_RATE = 16000
OWW_FRAME = 1280
VAD_FRAME_MS = 20
VAD_FRAME = SAMPLE_RATE * VAD_FRAME_MS // 1000
WAKE_THRESHOLD = 0.3
SILENCE_MS_TO_STOP = 400
MIN_VOICE_MS = 300
MAX_UTTERANCE_MS = 8000
PUSH_TO_TALK_MAX_MS = int(os.getenv("PUSH_TO_TALK_MAX_MS", "12000"))
PUSH_TO_TALK_MODE = os.getenv("PUSH_TO_TALK_MODE", "enter_stop").lower()

_pa = None
_stream = None
_oww = None
_vad = None
_capture_rate = SAMPLE_RATE


def _encontrar_dispositivo():
    preferidos = ("i2s", "snd_rpi_simple", "snd-i2s", "inmp441",
                  "usb", "voicehat", "googlevoice", "snd_rpi_google")
    candidatos = []
    for i in range(_pa.get_device_count()):
        info = _pa.get_device_info_by_index(i)
        if info['maxInputChannels'] <= 0:
            continue
        nombre_low = info['name'].lower()
        for prio, clave in enumerate(preferidos):
            if clave in nombre_low:
                candidatos.append((prio, i, info['name']))
                break
        else:
            candidatos.append((99, i, info['name']))
    if not candidatos:
        print("⚠️ Ningún dispositivo de entrada detectado. Usando default.")
        return None
    candidatos.sort()
    prio, idx, nombre = candidatos[0]
    print(f"🎤 Micro detectado: [{idx}] {nombre}")
    return idx


def _abrir_stream(idx):
    global _capture_rate
    for rate in (16000, 48000):
        try:
            buffer_frames = OWW_FRAME * rate // SAMPLE_RATE
            stream = _pa.open(
                rate=rate, channels=1, format=pyaudio.paInt16,
                input=True, frames_per_buffer=buffer_frames,
                input_device_index=idx,
            )
            _capture_rate = rate
            if rate != SAMPLE_RATE:
                print(f"🎤 Micro abierto a {rate} Hz (resample a {SAMPLE_RATE} Hz activo)")
            else:
                print(f"🎤 Micro abierto a {rate} Hz")
            return stream
        except OSError as e:
            print(f"   · rate {rate} no soportado ({e}); probando otro…")
    raise RuntimeError("Ningún sample rate funciona con este micro")


def _leer_raw(samples_16k):
    factor = _capture_rate // SAMPLE_RATE
    raw = _stream.read(samples_16k * factor, exception_on_overflow=False)
    if factor == 1:
        return raw
    audio = np.frombuffer(raw, dtype=np.int16)[::factor]
    return audio.tobytes()


def inicializar(use_wake_word=True):
    global _pa, _stream, _oww, _vad
    _pa = pyaudio.PyAudio()
    _stream = _abrir_stream(_encontrar_dispositivo())

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
    _ultimo_log = 0.0
    while True:
        raw = _leer_raw(OWW_FRAME)
        audio = np.frombuffer(raw, dtype=np.int16)
        scores = _oww.predict(audio)
        mejor = max(scores.values())
        if mejor > 0.05 and abs(mejor - _ultimo_log) > 0.02:
            print(f"   🔍 score wake={mejor:.3f} (threshold {WAKE_THRESHOLD})")
            _ultimo_log = mejor
        if mejor > WAKE_THRESHOLD:
            return


def _esperar_voz(timeout_ms):
    if _vad is None:
        return None
    ms_esperados = 0
    while ms_esperados < timeout_ms:
        frame = _leer_raw(VAD_FRAME)
        if _vad.is_speech(frame, SAMPLE_RATE):
            return frame
        ms_esperados += VAD_FRAME_MS
    return None


def _guardar_wav(buffer_audio):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        path = tmp.name

    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(bytes(buffer_audio))
    return path


def _grabar_desde(frame_inicial=b""):
    if _vad is None:
        return _grabar_manual()

    luces.cambiar_estado("escuchando")
    buffer_audio = bytearray(frame_inicial)
    silencio_ms = 0
    voz_ms = VAD_FRAME_MS if frame_inicial else 0
    inicio = time.time()

    while True:
        frame = _leer_raw(VAD_FRAME)
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

    return _guardar_wav(buffer_audio)


def _grabar_manual(max_ms=PUSH_TO_TALK_MAX_MS):
    if PUSH_TO_TALK_MODE in ("enter_stop", "manual_stop", "stop_enter"):
        return _grabar_hasta_enter(max_ms=max_ms)

    luces.cambiar_estado("escuchando")
    buffer_audio = bytearray()
    inicio = time.time()
    print(f"🎙️ Grabando {max_ms // 1000}s como máximo. Habla ahora...")

    while (time.time() - inicio) * 1000 < max_ms:
        buffer_audio += _leer_raw(VAD_FRAME)

    return _guardar_wav(buffer_audio)


def _grabar_hasta_enter(max_ms=PUSH_TO_TALK_MAX_MS):
    luces.cambiar_estado("escuchando")
    buffer_audio = bytearray()
    stop_event = threading.Event()

    def _wait_enter():
        input("Pulsa ENTER otra vez para parar la grabación... ")
        stop_event.set()

    threading.Thread(target=_wait_enter, daemon=True).start()
    inicio = time.time()
    print(f"🎙️ Grabando. Habla ahora. Límite máximo: {max_ms // 1000}s.")

    while not stop_event.is_set() and (time.time() - inicio) * 1000 < max_ms:
        buffer_audio += _leer_raw(VAD_FRAME)

    return _guardar_wav(buffer_audio)


def _transcribir_deepgram(path):
    url = "https://api.deepgram.com/v1/listen?model=nova-3&language=es&smart_format=true"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/wav",
    }
    try:
        with open(path, "rb") as audio:
            response = requests.post(url, headers=headers, data=audio, timeout=10)

        if os.path.exists(path):
            os.remove(path)

        if response.status_code == 200:
            return response.json()['results']['channels'][0]['alternatives'][0]['transcript']
        print(f"⚠️ Error Deepgram: {response.status_code} {response.text[:160]}")
        return ""
    except Exception as e:
        print(f"⚠️ Error de conexión: {e}")
        return ""


def escuchar():
    print("💤 En reposo. Di la wake word para despertarme...")
    _esperar_wake()
    print("🎤 [Wake] ¡Despierto! Escuchando tu petición...")
    wav = _grabar_desde()
    print("🧠 [Deepgram] Analizando...")
    return _transcribir_deepgram(wav)


def escuchar_push_to_talk():
    input("\nPulsa ENTER para empezar a grabar... ")
    wav = _grabar_manual()
    print("🧠 [Deepgram] Analizando...")
    return _transcribir_deepgram(wav)


def escuchar_seguimiento(timeout_ms=8000):
    if _vad is None:
        return escuchar_push_to_talk()

    print(f"👂 ¿Algo más? ({timeout_ms//1000}s)...")
    luces.cambiar_estado("escuchando")
    frame = _esperar_voz(timeout_ms)
    if frame is None:
        print("⌛ Silencio. Volviendo al modo radar.")
        return None
    print("🎤 Voz captada, grabando...")
    wav = _grabar_desde(frame)
    print("🧠 [Deepgram] Analizando...")
    return _transcribir_deepgram(wav)


def cerrar():
    global _stream, _pa
    if _stream:
        try:
            _stream.stop_stream()
            _stream.close()
        except Exception:
            pass
        _stream = None
    if _pa:
        try:
            _pa.terminate()
        except Exception:
            pass
        _pa = None
