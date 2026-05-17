import os
import tempfile
import threading
import time
import wave

import numpy as np
import pyaudio

import luces

SAMPLE_RATE = 16000
OWW_FRAME = 1280
VAD_FRAME_MS = 20
VAD_FRAME = SAMPLE_RATE * VAD_FRAME_MS // 1000
PUSH_TO_TALK_MAX_MS = int(os.getenv("PUSH_TO_TALK_MAX_MS", "12000"))
PUSH_TO_TALK_MODE = os.getenv("PUSH_TO_TALK_MODE", "enter_stop").lower()


class AudioInput:
    def __init__(self):
        self.pa = None
        self.stream = None
        self.capture_rate = SAMPLE_RATE

    def inicializar(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self._abrir_stream(self._encontrar_dispositivo())

    def cerrar(self):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        if self.pa:
            try:
                self.pa.terminate()
            except Exception:
                pass
            self.pa = None

    def _encontrar_dispositivo(self):
        preferidos = (
            "i2s",
            "snd_rpi_simple",
            "snd-i2s",
            "inmp441",
            "usb",
            "voicehat",
            "googlevoice",
            "snd_rpi_google",
        )
        candidatos = []
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            if info["maxInputChannels"] <= 0:
                continue
            nombre_low = info["name"].lower()
            for prio, clave in enumerate(preferidos):
                if clave in nombre_low:
                    candidatos.append((prio, i, info["name"]))
                    break
            else:
                candidatos.append((99, i, info["name"]))

        if not candidatos:
            print("⚠️ Ningún dispositivo de entrada detectado. Usando default.")
            return None

        candidatos.sort()
        prio, idx, nombre = candidatos[0]
        print(f"🎤 Micro detectado: [{idx}] {nombre}")
        return idx

    def _abrir_stream(self, idx):
        for rate in (16000, 48000):
            try:
                buffer_frames = OWW_FRAME * rate // SAMPLE_RATE
                stream = self.pa.open(
                    rate=rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=buffer_frames,
                    input_device_index=idx,
                )
                self.capture_rate = rate
                if rate != SAMPLE_RATE:
                    print(f"🎤 Micro abierto a {rate} Hz (resample a {SAMPLE_RATE} Hz activo)")
                else:
                    print(f"🎤 Micro abierto a {rate} Hz")
                return stream
            except OSError as e:
                print(f"   · rate {rate} no soportado ({e}); probando otro…")

        raise RuntimeError("Ningún sample rate funciona con este micro")

    def leer_raw(self, samples_16k):
        factor = self.capture_rate // SAMPLE_RATE
        raw = self.stream.read(samples_16k * factor, exception_on_overflow=False)
        if factor == 1:
            return raw
        audio = np.frombuffer(raw, dtype=np.int16)[::factor]
        return audio.tobytes()

    def guardar_wav(self, buffer_audio):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            path = tmp.name

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(bytes(buffer_audio))
        return path

    def grabar_fijo(self, max_ms=PUSH_TO_TALK_MAX_MS):
        luces.cambiar_estado("escuchando")
        buffer_audio = bytearray()
        inicio = time.time()
        print(f"🎙️ Grabando {max_ms // 1000}s como máximo. Habla ahora...")

        while (time.time() - inicio) * 1000 < max_ms:
            buffer_audio += self.leer_raw(VAD_FRAME)

        return self.guardar_wav(buffer_audio)

    def grabar_hasta_enter(self, max_ms=PUSH_TO_TALK_MAX_MS):
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
            buffer_audio += self.leer_raw(VAD_FRAME)

        return self.guardar_wav(buffer_audio)

    def grabar_manual(self, max_ms=PUSH_TO_TALK_MAX_MS):
        if PUSH_TO_TALK_MODE in ("enter_stop", "manual_stop", "stop_enter"):
            return self.grabar_hasta_enter(max_ms=max_ms)
        return self.grabar_fijo(max_ms=max_ms)
