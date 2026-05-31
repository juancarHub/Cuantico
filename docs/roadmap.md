# Hoja de ruta de Atlantis

Este documento resume la dirección de desarrollo de Atlantis Assistant y se irá actualizando según se completen, cambien o reordenen los bloques.

## Estado actual validado

### v0.1.x — MVP funcional

Base inicial del asistente:

```text
- entrada manual / voz
- selección de proveedores
- cara visual
- interacción táctil básica
- funcionamiento en tablet
```

### v0.2.x — Baja latencia y experiencia conversacional

Bloque de fluidez:

```text
- LLM streaming
- TTS por frases
- pipeline separado TTS/playback
- métricas STT / LLM-stream-first / FIRST_AUDIO / TTS / STREAM_SESSION_TOTAL
- interrupción suave por toque durante el habla
```

### v0.3.x — Identidad, prompt y configuración

Bloque de desacoplamiento:

```text
- prompt externo en prompts/atlantis_system.txt
- ASSISTANT_NAME configurable
- SYSTEM_PROMPT_PATH configurable
- identidad centralizada en prompt, logs y UI
- .env.example
- documentación de persona y configuración
```

## Siguiente fase: v0.4.x — Capa de herramientas

Objetivo: pasar de asistente conversacional a agente capaz de ejecutar acciones reales de forma modular, sin convertir `main_minimal.py` en un fichero monolítico.

### v0.4.0 — Tool layer

Crear una capa común para registrar herramientas:

```text
src/agent_tools/
  __init__.py
  registry.py
  memory_tools.py
```

Objetivos:

```text
- mover recordar / olvidar / listar_recuerdos fuera de main_minimal.py
- crear build_tools()
- dejar main_minimal.py usando una lista de tools externa
- preparar el terreno para filesystem, timers, listas, web y calendar
```

### v0.4.1 — Filesystem sandbox

Dar a Atlantis capacidad de leer y escribir archivos locales, pero solo dentro de una carpeta controlada.

Propuesta:

```text
workspace/
  notes/
  logs/
  lists/
  prompt_drafts/
```

Tools iniciales:

```text
listar_archivos(carpeta)
leer_archivo(ruta_relativa)
escribir_archivo(ruta_relativa, contenido)
anexar_archivo(ruta_relativa, contenido)
```

Regla de seguridad:

```text
Todas las rutas deben resolverse dentro de ATLANTIS_WORKSPACE_DIR.
No se permite acceso libre al disco.
```

Usos previstos:

```text
- logs de casa
- notas persistentes
- borradores de prompt
- registros de sensores/eventos
- documentos simples mantenidos por el asistente
```

### v0.4.2 — Temporizadores

Temporizadores independientes del daemon de Home Assistant.

Tools previstas:

```text
crear_timer(nombre, duracion, mensaje)
listar_timers()
cancelar_timer(id_o_nombre)
```

Comportamiento objetivo:

```text
usuario pide un temporizador
↓
Atlantis lo crea
↓
al terminar suena un aviso
↓
la cara cambia a aviso/espera
↓
al acudir, Atlantis explica qué temporizador terminó
```

Primera implementación probable:

```text
- hilos o scheduler interno en proceso
- aviso WAV desde Python
- persistencia opcional posterior
```

### v0.4.3 — Listas y tareas en SQLite

Estado operativo estructurado, separado de la memoria conversacional.

Casos de uso:

```text
- lista de la compra
- tareas de casa
- tareas del jardín
- pendientes del proyecto
- mantenimientos
```

Modelo inicial propuesto:

```text
lists
  id
  name
  created_at

list_items
  id
  list_id
  text
  status
  due_date
  duration_minutes
  notes
  created_at
  updated_at
```

Tools previstas:

```text
crear_lista(nombre)
añadir_item(lista, texto, fecha_prevista, duracion, notas)
listar_items(lista)
marcar_item_hecho(lista, item)
borrar_item(lista, item)
```

### v0.4.4 — Búsqueda web

Dar a Atlantis capacidad de consultar información actual.

Tool inicial:

```text
buscar_web(consulta, max_resultados)
```

Objetivos:

```text
- responder preguntas de actualidad
- obtener datos externos recientes
- apoyar decisiones con fuentes
```

Se estudiará si conviene usar:

```text
- API de búsqueda externa
- herramientas/respuestas OpenAI con búsqueda
- módulo backend propio
```

### v0.4.5 — Google Calendar

Recuperar/adaptar la integración que tenía Cuántico.

Primera fase recomendada:

```text
- lectura de eventos
- consultas tipo: qué tengo hoy / mañana / esta semana
```

Segunda fase:

```text
- crear eventos
- modificar eventos
- borrar eventos con confirmación
```

Tools previstas:

```text
listar_eventos(fecha_inicio, fecha_fin)
crear_evento(titulo, fecha, hora, duracion, descripcion)
```

## Fase posterior: v0.5.x — Memoria nueva

La memoria actual cumple función MVP, pero se rediseñará más adelante.

Objetivos probables:

```text
- memoria explícita por intención
- recuerdos revisables
- categorías
- importancia/prioridad
- edición y borrado controlado
- evitar tool calls no deseadas durante streaming
- posible resumen episódico
```

## Fase posterior: v0.6.x — Daemon, Home Assistant y bus de eventos

Redis no se considera necesario para la fase inmediata de tools locales.

Redis puede tener sentido cuando Atlantis pase de proceso único a arquitectura con varios subsistemas:

```text
- daemon de Home Assistant
- eventos de sensores
- notificaciones externas
- timers persistentes
- workers separados
- estado compartido
```

Posible bus futuro:

```text
atlantis.events
atlantis.timers
atlantis.notifications
atlantis.home
```

Criterio actual:

```text
No introducir Redis hasta que aporte valor real.
Primero tools modulares dentro del proceso.
Después, si el sistema pide concurrencia o workers, estudiar Redis/event bus.
```

## Acceso desde móvil

Bloque futuro, posterior a las herramientas básicas.

Opciones a estudiar:

```text
- HTTP local con FastAPI
- webapp móvil
- aplicación dedicada
- acceso seguro vía VPN/Tailscale
```

Primera forma probable:

```text
/api/state
/api/say
/api/tools
/api/timers
/api/lists
```

## Principios de arquitectura

```text
- mantener main_minimal.py pequeño
- cada capacidad nueva debe vivir en su módulo
- evitar acceso libre al sistema sin sandbox
- documentar cada bloque estable
- taggear los puntos validados
- no introducir Redis/daemon antes de necesitarlo
- priorizar fluidez y estabilidad de la experiencia en tablet
```
