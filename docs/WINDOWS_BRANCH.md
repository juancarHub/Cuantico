# Cuántico Windows Branch

Documento técnico de la rama `Windows_Branch`.

Esta rama adapta Cuántico para ejecutarse en una tablet/PC Windows sin depender de Raspberry Pi, GPIO, NeoPixel físico, `sox`, `aplay` ni servicios Linux para el MVP mínimo.

## Objetivo actual

Construir un MVP conversacional portable con:

- cara animada en pantalla;
- entrada por texto o push-to-talk;
- STT intercambiable;
- LLM intercambiable;
- TTS intercambiable;
- memoria persistente básica;
- compatibilidad futura con Raspberry.

El objetivo inmediato no es portar todas las integraciones del proyecto original. Spotify, Govee, Calendar, YouTube y llamadas quedan para fases posteriores.

## Estado funcional actual

Probado en Windows:

- `main_minimal.py` funciona.
- `DISPLAY_BACKEND=screen` muestra la cara PySide6.
- `INPUT_MODE=text` funciona.
- `INPUT_MODE=push_to_talk` funciona con PyAudio.
- `STT_PROVIDER=deepgram` y `STT_PROVIDER=openai` funcionan.
- `TTS_PROVIDER=elevenlabs` y `TTS_PROVIDER=openai` funcionan.
- `LLM_PROVIDER=openai` funciona.

## Entrada principal recomendada

Para Windows/tablet se usa:

```bash
python src/main_minimal.py
```

`src/main.py` conserva más lógica del proyecto original y todavía inicializa integraciones externas.

## Arquitectura actual

```text
src/
  main_minimal.py      # runtime mínimo Windows/tablet
  llm.py               # proveedor LLM configurable
  micro.py             # captura de audio + entrega al STT
  altavoz.py           # salida/reproducción de audio + fachada TTS
  luces.py             # fachada visual compatible

  display/
    base.py
    factory.py
    null_display.py
    neopixel_display.py
    screen_display.py

  stt/
    base.py
    factory.py
    deepgram_stt.py
    openai_stt.py

  tts/
    base.py
    factory.py
    elevenlabs_tts.py
    openai_tts.py
```

## Capas desacopladas

### Display

Seleccionado por:

```env
DISPLAY_BACKEND=screen
SCREEN_DISPLAY_MODE=window
```

Valores útiles:

```env
DISPLAY_BACKEND=screen      # cara PySide6
DISPLAY_BACKEND=null        # sin UI
DISPLAY_BACKEND=neopixel    # Raspberry/NeoPixel

SCREEN_DISPLAY_MODE=window
SCREEN_DISPLAY_MODE=fullscreen
```

### Input

Seleccionado por:

```env
INPUT_MODE=push_to_talk
```

Valores útiles:

```env
INPUT_MODE=text             # entrada por consola
INPUT_MODE=push_to_talk     # Enter para grabar / Enter para cortar
INPUT_MODE=voice            # wake word, pendiente de estabilizar en Windows
```

Push-to-talk:

```env
PUSH_TO_TALK_MODE=enter_stop
PUSH_TO_TALK_MAX_MS=30000
```

### STT

Seleccionado por:

```env
STT_PROVIDER=openai
```

Valores:

```env
STT_PROVIDER=openai
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
OPENAI_STT_LANGUAGE=es
```

O:

```env
STT_PROVIDER=deepgram
DEEPGRAM_API_KEY=...
```

### LLM

Seleccionado por:

```env
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
```

Gemini se mantiene como alternativa:

```env
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-3-flash-preview
```

### TTS

Seleccionado por:

```env
TTS_PROVIDER=openai
```

Valores:

```env
TTS_PROVIDER=openai
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=alloy
```

O:

```env
TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
```

### Audio output

En Windows:

```env
AUDIO_OUTPUT_BACKEND=windows
```

También acepta:

```env
AUDIO_OUTPUT_BACKEND=file
AUDIO_OUTPUT_BACKEND=playsound
```

En Raspberry/Linux puede usarse:

```env
AUDIO_OUTPUT_BACKEND=linux
```

## Ejemplo de configuración Windows mínima

```env
DISPLAY_BACKEND=screen
SCREEN_DISPLAY_MODE=window

INPUT_MODE=push_to_talk
PUSH_TO_TALK_MODE=enter_stop
PUSH_TO_TALK_MAX_MS=30000

LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini

STT_PROVIDER=openai
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
OPENAI_STT_LANGUAGE=es

TTS_PROVIDER=openai
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=alloy

AUDIO_OUTPUT_BACKEND=windows
```

Ejemplo híbrido:

```env
LLM_PROVIDER=openai
STT_PROVIDER=deepgram
TTS_PROVIDER=elevenlabs
```

## Instalación Windows

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install PySide6 playsound==1.2.2 openai pyaudio numpy
```

Notas:

- `webrtcvad` puede fallar en Windows si no están instaladas las Microsoft C++ Build Tools.
- El modo `push_to_talk` actual no necesita `webrtcvad` ni `openwakeword`.
- `openwakeword` queda para una fase posterior de wake word.

## Flujo de ejecución de `main_minimal.py`

```text
luces.encender_reactor()
recuerdos.inicializar()
micro.inicializar(use_wake_word=False)

loop:
  micro.escuchar_push_to_talk()
    -> captura WAV
    -> stt.transcribe(path)
  llm.chat.send_message(texto)
  altavoz.hablar(respuesta, emocion)
    -> tts.generate_to_file(texto)
    -> playsound(path)
  luces.cambiar_estado(emocion)
```

## Diseño de compatibilidad

La rama mantiene fachadas históricas para no romper el código original:

- `luces.cambiar_estado(...)`
- `luces.encender_reactor()`
- `altavoz.hablar(...)`
- `micro.escuchar(...)`

Por debajo, cada fachada delega en backends configurables.

## Pendientes técnicos

### Corto plazo

- Mover reproducción local a `src/audio/output.py`.
- Mover captura PyAudio a `src/audio/input.py`.
- Añadir launcher `.bat` para Windows.
- Separar requirements por plataforma.
- Revisar `.env.example`.

### Medio plazo

- Modo escucha automática sin `webrtcvad`, posiblemente con RMS/energía simple.
- Wake word real en Windows.
- Sincronización de boca con TTS.
- Estados emocionales más expresivos.
- Reintegrar herramientas opcionales por módulos: Spotify, Govee, Calendar, YouTube.

### Futuro

- Modo OpenAI Realtime experimental.
- Empaquetado como app Windows.
- Modo Linux desktop.
- Backend tablet fullscreen estable.

## Principio de diseño

Cada proveedor externo debe ser intercambiable por configuración, no por cambios de código.

```text
LLM_PROVIDER
STT_PROVIDER
TTS_PROVIDER
DISPLAY_BACKEND
AUDIO_OUTPUT_BACKEND
INPUT_MODE
```

La meta es que Cuántico no dependa de un único proveedor ni de una única plataforma.
