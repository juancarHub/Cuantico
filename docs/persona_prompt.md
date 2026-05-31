# Persona y prompt del asistente

Este documento describe cómo Atlantis separa la identidad/persona del código Python.

## Variables principales

La identidad activa se controla desde `.env`:

```env
ASSISTANT_NAME=Atlantis
SYSTEM_PROMPT_PATH=prompts/atlantis_system.txt
```

## ASSISTANT_NAME

`ASSISTANT_NAME` define el nombre operativo del asistente.

Actualmente se usa para:

```text
- banner de arranque
- logs de conversación
- título de la ventana visual
- marcador dinámico dentro del prompt del sistema
```

Ejemplo:

```env
ASSISTANT_NAME=Atlantis
```

Al arrancar debe verse algo similar a:

```text
🚀 ATLANTIS MINIMAL: VOZ + CARA + LLM
🪪 Assistant name: Atlantis
```

## SYSTEM_PROMPT_PATH

`SYSTEM_PROMPT_PATH` indica el fichero de prompt/persona que se carga al arrancar.

Por defecto, si no se define en `.env`, `config.py` usa:

```text
prompts/atlantis_system.txt
```

Ejemplo explícito:

```env
SYSTEM_PROMPT_PATH=prompts/atlantis_system.txt
```

Las rutas relativas se resuelven desde la raíz del repositorio.

## Prompt externo

El prompt activo vive en:

```text
prompts/atlantis_system.txt
```

Ese fichero contiene el texto de personalidad y comportamiento general del asistente.

El código carga ese fichero desde `main_minimal.py` mediante:

```text
_cargar_system_prompt()
```

Si el fichero externo no existe, el sistema usa un prompt interno de fallback para no impedir el arranque.

## Marcadores dinámicos

El prompt externo puede contener marcadores que el código sustituye al arrancar.

### {assistant_name}

Se sustituye por el valor de `config.ASSISTANT_NAME`.

Ejemplo dentro del prompt:

```text
Eres {assistant_name}, una IA con carácter que vive en una tablet Windows.
```

Si en `.env` hay:

```env
ASSISTANT_NAME=Atlantis
```

el modelo recibe:

```text
Eres Atlantis, una IA con carácter que vive en una tablet Windows.
```

### {emotion_control_instructions}

Se sustituye por el bloque generado desde:

```text
src/emotions.py
```

Ese bloque define el protocolo de salida emocional, por ejemplo:

```text
emocion: cariño
respuesta...
```

El prompt externo debe mantener este marcador si se quiere conservar el sistema visual/emocional actual.

## Regla importante

Los marcadores deben escribirse exactamente así:

```text
{assistant_name}
{emotion_control_instructions}
```

No deben escribirse con espacios ni variantes como:

```text
{assistant name}
assistant name
{emotion control instructions}
```

Si el marcador está mal escrito, el modelo puede recibirlo literalmente y decirlo en voz.

## Flujo de carga

```text
.env
↓
config.py
↓
ASSISTANT_NAME / SYSTEM_PROMPT_PATH
↓
main_minimal.py
↓
lee prompts/atlantis_system.txt
↓
sustituye marcadores
↓
añade fecha actual
↓
añade recuerdos persistentes si existen
↓
crea el chat del proveedor LLM
```

## Edición segura del prompt

Para modificar la personalidad:

```text
1. editar prompts/atlantis_system.txt
2. conservar los marcadores dinámicos necesarios
3. guardar
4. reiniciar Atlantis
```

No hace falta tocar código Python para cambiar tono, estilo, nombre textual dentro del prompt o reglas de conversación.

## Estado validado

Esta arquitectura fue validada después del tag:

```text
v0.3.0-tablet_Stable_ExternalPrompt
```

Y se complementa con la limpieza de identidad:

```text
ASSISTANT_NAME centralizado en prompt, consola y UI.
```
