# Cuantico World

Cuantico World mantiene una representacion persistente y auditable del ecosistema de Cuantico. Los eventos se guardan y proyectan sin pasar por el LLM.

## Flujo

```text
nodo/daemon/usuario
  -> POST /api/v1/events
  -> autenticacion
  -> transaccion SQLite
       insertar world_events
       actualizar proyecciones
  -> 200 OK
```

La base vive en `state/cuantico_world.db`, usa WAL y queda fuera de Git.

## Tablas iniciales

- `world_events`: historial inmutable, ordenado y deduplicado por `event_id`.
- `world_rooms`: ocupacion actual y ultima observacion por habitacion.
- `world_room_people`: identidades conocidas presentes en cada habitacion.
- `world_people`: ubicacion actual, ultimo lugar y ultima vez que se vio cada persona.
- `world_actions`: intenciones y resultados de acciones futuras.
- `world_schedules`: acciones programadas.
- `world_rules`: reglas estructuradas confirmadas por el usuario.
- `assistant_runtime`: estado vital de Cuantico.

Las tablas de acciones, reglas y programacion constituyen el contrato interno. Su adaptador al daemon se completara cuando este disponible el contrato real.

## Semantica temporal

`occurred_at` decide si un evento puede modificar la proyeccion. Un evento atrasado se conserva, pero no pisa un estado mas reciente. `received_at` indica cuando llego a Cuantico.

Los duplicados conservan una unica fila porque `event_id` es unico. La operacion `rebuild_projections()` permite borrar las vistas derivadas y reconstruirlas reproduciendo el historial FIFO.

## Personas

`current_location` representa donde se considera que esta ahora. `last_seen_location` y `last_seen_at` sobreviven a una salida. Por tanto, tras salir del comedor:

```text
current_location = null
last_seen_location = comedor
```

## Acceso del modelo

El modelo no tiene acceso SQL. Usa las tools:

- `consultar_habitacion(nombre)`
- `consultar_persona(nombre)`
- `consultar_mundo()`

Ademas recibe un resumen pequeno del estado actual en cada turno. Las futuras tools de escritura validaran y registraran eventos; nunca modificaran tablas directamente.

## API de inspeccion

Requiere el token administrativo:

```text
GET /api/v1/world
GET /api/v1/world/rooms/{room}
GET /api/v1/events?limit=50
```
