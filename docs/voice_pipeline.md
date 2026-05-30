# Atlantis voice pipeline

Este documento describe la arquitectura actual del flujo de voz de Atlantis en modo tablet.

## Objetivo

Reducir la latencia percibida entre el final del habla del usuario y el inicio de la respuesta hablada del asistente, manteniendo sincronía visual con la cara animada.

## Flujo general

```text
pantalla táctil / click
↓
grabación por tap_or_silence
↓
STT
↓
LLM streaming
↓
extracción de emoción
↓
corte de texto por frases
↓
cola de frases
↓
worker TTS
↓
cola de audios listos
↓
worker playback
↓
estado visual hablando:<emocion>
```

## Entrada de voz

El modo principal de tablet es:

```env
INPUT_MODE=push_to_talk
PUSH_TO_TALK_MODE=tap_or_silence
```

El usuario toca la cara para empezar a grabar. La grabación termina si ocurre uno de estos casos:

```text
1. el usuario toca de nuevo la pantalla
2. se detecta silencio durante AUTO_STOP_SILENCE_MS
3. se alcanza PUSH_TO_TALK_MAX_MS
```

Variables relacionadas:

```env
AUTO_STOP_SILENCE_MS=1800
AUTO_STOP_MIN_VOICE_MS=600
AUTO_STOP_RMS_THRESHOLD=500
PUSH_TO_TALK_MAX_MS=12000
```

## STT

El audio grabado se guarda como WAV temporal y se envía al proveedor STT configurado:

```env
STT_PROVIDER=openai
```

Con `DEBUG_LATENCY=true`, se mide:

```text
⏱️ STT(openai): X.XXs
```

## LLM streaming

Cuando está activado:

```env
ENABLE_LLM_STREAMING=true
```

`main_minimal.py` llama a:

```python
chat.stream_message(texto_usuario)
```

En OpenAI, `llm.py` usa `chat.completions.create(..., stream=True)`.

En providers sin streaming o en casos no soportados, se usa fallback a `send_message()`.

## Tools y memoria

Si durante el streaming OpenAI intenta hacer `tool_calls`, el streaming se aborta y se usa fallback normal.

Esto protege tools como:

```text
recordar
olvidar
listar_recuerdos
```

La consecuencia es que preguntas relacionadas con memoria pueden ser menos fluidas, pero mantienen seguridad funcional.

## Línea de emoción

El prompt obliga a empezar la respuesta con una línea de control:

```text
emocion: cariño
```

`main_minimal.py` acumula chunks iniciales hasta detectar esa línea. Luego limpia la línea de control y pasa solo el texto hablado al altavoz.

El catálogo de emociones vive en:

```text
src/emotions.py
```

Emociones actuales:

```text
neutral
sarcasmo
enfadado
cachondeo
aburrido
cariño
```

## Pipeline de TTS y reproducción

`altavoz.hablar_stream()` separa el texto en frases usando puntuación:

```text
. ! ? saltos de línea
```

Después usa dos workers:

```text
worker TTS
  consume cola de frases
  genera archivos de audio temporales
  los pone en cola de audios

worker PLAY
  consume cola de audios
  cambia estado visual a hablando:<emocion>
  reproduce el audio
  borra el archivo temporal
```

Esto permite que, mientras una frase se reproduce, la siguiente pueda estar generándose.

## Sincronía visual

El estado visual `hablando:<emocion>` se activa justo antes de reproducir audio, no durante la generación TTS.

Esto evita el fallo perceptivo anterior:

```text
la cara habla
↓
1-2 segundos de silencio
↓
empieza el audio
```

Ahora la cara pasa a hablar prácticamente cuando comienza la reproducción.

## Métricas actuales

Con `DEBUG_LATENCY=true` se imprimen métricas como:

```text
⏱️ STT(openai): X.XXs
⏱️ LLM-stream-first(openai): X.XXs
⏱️ TTS(OpenAI): X.XXs
⏱️ LLM-stream-total(openai): X.XXs
```

Nota: `LLM-stream-total` ya no mide solo el LLM. En el pipeline actual representa aproximadamente la sesión completa de streaming, TTS y reproducción. Debe renombrarse en una futura limpieza a algo como:

```text
STREAM_SESSION_TOTAL
```

También queda pendiente añadir una métrica explícita:

```text
FIRST_AUDIO
```

para medir el tiempo real hasta el primer sonido audible.

## Estado estable

El punto funcional validado está etiquetado como:

```text
v0.2.1-tablet_Stable_AgentePipeline
```

Ese punto incluye:

```text
LLM streaming
TTS por frases
cola TTS
cola playback
sincronía visual con reproducción
```
