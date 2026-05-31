# Configuración de Atlantis

Este documento describe la configuración principal de Atlantis Assistant y cómo preparar un entorno nuevo a partir de `.env.example`.

## Crear el `.env`

El repositorio incluye una plantilla:

```text
.env.example
```

Para preparar una instalación nueva:

```bash
copy .env.example .env
```

o en Linux/macOS:

```bash
cp .env.example .env
```

Después edita `.env` y rellena las claves reales. El fichero `.env` no debe subirse al repositorio.

## Identidad y persona

```env
ASSISTANT_NAME=Atlantis
SYSTEM_PROMPT_PATH=prompts/atlantis_system.txt
```

`ASSISTANT_NAME` controla el nombre operativo del asistente. Se usa en consola, título de ventana y dentro del prompt mediante el marcador `{assistant_name}`.

`SYSTEM_PROMPT_PATH` apunta al fichero de personalidad. Por defecto se usa:

```text
prompts/atlantis_system.txt
```

Las rutas relativas se resuelven desde la raíz del repositorio.

## Display

```env
DISPLAY_BACKEND=screen
SCREEN_DISPLAY_MODE=window
```

`DISPLAY_BACKEND=screen` activa la cara visual en pantalla.

`SCREEN_DISPLAY_MODE` puede usarse como:

```env
SCREEN_DISPLAY_MODE=window
SCREEN_DISPLAY_MODE=tablet
SCREEN_DISPLAY_MODE=fullscreen
```

Para tablet, normalmente interesa `tablet` o `fullscreen`.

## Entrada de voz / interacción tablet

```env
INPUT_MODE=push_to_talk
PUSH_TO_TALK_MODE=tap_or_silence
PUSH_TO_TALK_MAX_MS=12000
AUTO_STOP_SILENCE_MS=1800
AUTO_STOP_MIN_VOICE_MS=600
AUTO_STOP_RMS_THRESHOLD=500
```

Flujo recomendado para tablet:

```text
tocar cara
↓
grabar voz
↓
tocar de nuevo o esperar silencio
↓
enviar audio
```

`AUTO_STOP_SILENCE_MS` define cuántos milisegundos de silencio provocan el envío automático.

`AUTO_STOP_MIN_VOICE_MS` evita cortar demasiado pronto si todavía no se ha detectado voz suficiente.

`AUTO_STOP_RMS_THRESHOLD` es el umbral de energía de audio usado para distinguir voz/ruido. Si corta demasiado pronto, puede estar alto. Si tarda mucho en detectar silencio, puede estar bajo o el entorno puede tener ruido.

`PUSH_TO_TALK_MAX_MS` limita la duración máxima de grabación.

## LLM

```env
LLM_PROVIDER=openai
ENABLE_LLM_STREAMING=true
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
```

`LLM_PROVIDER=openai` usa OpenAI como proveedor principal.

`ENABLE_LLM_STREAMING=true` activa respuesta por streaming. Esto permite empezar el TTS antes de tener la respuesta completa.

`OPENAI_API_KEY` debe rellenarse en `.env` real.

También existe configuración opcional para Gemini:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3-flash-preview
```

## STT / transcripción

```env
STT_PROVIDER=openai
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
OPENAI_STT_LANGUAGE=es
```

Configuración recomendada actual:

```env
STT_PROVIDER=openai
```

Deepgram queda como alternativa opcional:

```env
DEEPGRAM_API_KEY=
```

## TTS / voz

```env
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=alloy
OPENAI_TTS_SPEED=1.0
OPENAI_TTS_FORMAT=mp3
```

`OPENAI_TTS_SPEED` permite ajustar la velocidad de habla. Valores por debajo de `1.0` hablan más lento; valores por encima de `1.0` hablan más rápido.

`OPENAI_TTS_FORMAT=mp3` es una opción práctica en Windows con el backend actual.

ElevenLabs queda como alternativa opcional:

```env
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb
```

## Salida de audio

```env
AUDIO_OUTPUT_BACKEND=auto
```

Opciones habituales:

```env
AUDIO_OUTPUT_BACKEND=auto
AUDIO_OUTPUT_BACKEND=playsound
```

En Windows, si falta `ffmpeg` o falla conversión a WAV, puede probarse `playsound` como backend alternativo.

## Métricas de latencia

```env
DEBUG_LATENCY=true
```

Cuando está activo, se imprimen métricas como:

```text
⏱️ STT(openai): ...
⏱️ LLM-stream-first(openai): ...
⏱️ FIRST_AUDIO(openai): ...
⏱️ TTS(OpenAI): ...
⏱️ STREAM_SESSION_TOTAL(openai): ...
```

`FIRST_AUDIO` mide el tiempo hasta el primer audio audible.

`STREAM_SESSION_TOTAL` mide la sesión completa de respuesta hablada, incluyendo streaming, TTS y reproducción.

Si la respuesta se interrumpe con un toque durante el habla, puede aparecer:

```text
⏱️ STREAM_INTERRUPTED(openai): ...
```

## Interrupción de voz

Durante la reproducción, tocar la cara solicita una interrupción suave:

```text
hablando
↓
tap en la cara
↓
termina la frase actual
↓
descarta audio pendiente
↓
vuelve a esperando
```

No corta la frase en seco; espera a que termine el bloque actual para evitar estados bruscos o errores de reproducción.

## Integraciones opcionales

El `.env.example` incluye variables para integraciones futuras o parcialmente implementadas:

```env
GOVEE_API_KEY=
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
GOOGLE_CLIENT_SECRETS_PATH=state/google_client.json
GOOGLE_TOKEN_PATH=state/google_token.json
YOUTUBE_CHANNEL_ID=
```

Pueden quedar vacías si no se usan todavía, salvo que el código cargado exija alguna clave concreta en el arranque.

## Configuración recomendada para tablet

```env
ASSISTANT_NAME=Atlantis
SYSTEM_PROMPT_PATH=prompts/atlantis_system.txt
DEBUG_LATENCY=true
DISPLAY_BACKEND=screen
SCREEN_DISPLAY_MODE=tablet
INPUT_MODE=push_to_talk
PUSH_TO_TALK_MODE=tap_or_silence
PUSH_TO_TALK_MAX_MS=12000
AUTO_STOP_SILENCE_MS=1800
AUTO_STOP_MIN_VOICE_MS=600
AUTO_STOP_RMS_THRESHOLD=500
LLM_PROVIDER=openai
ENABLE_LLM_STREAMING=true
STT_PROVIDER=openai
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
OPENAI_STT_LANGUAGE=es
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=alloy
OPENAI_TTS_SPEED=1.0
OPENAI_TTS_FORMAT=mp3
AUDIO_OUTPUT_BACKEND=auto
```

## Arranque esperado

Con la configuración correcta, el arranque debe mostrar algo similar a:

```text
🧾 System prompt cargado desde: .../prompts/atlantis_system.txt
🚀 ATLANTIS MINIMAL: VOZ + CARA + LLM
🧠 Provider configurado: openai
🎙️ Input mode: push_to_talk
🌊 LLM streaming: on
🪪 Assistant name: Atlantis
```
