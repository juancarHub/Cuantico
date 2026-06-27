# Primera regla

Atlantis **no trabaja con archivos**.

Trabaja con documentos.

Parece una tontería...

...pero cambia completamente la forma de pensar.

Ella no dirá:

```
abre C:\...
```

Dirá:

```
abre el documento "registro del huerto"añade esto al diariocrea una notaactualiza el informe
```

Es un nivel de abstracción mucho más natural.

---

# Segunda regla

Los documentos tienen identidad.

No existen porque estén en:

```
notes/pepito.txt
```

Existen porque son un documento.

Por eso me gustaría que desde el principio hubiera una pequeña tabla SQLite.

No para guardar el contenido.

Solo el índice.

Por ejemplo:

```
documentosidtitulotiporutacreadomodificadotagsdescripcion
```

Y luego el contenido vive en el fichero.

Así Atlantis puede preguntar:

```
SELECT *FROM documentosWHERE tags LIKE '%huerto%'
```

sin tener que abrir veinte archivos.

---

# Tercera regla

Los documentos pertenecen a categorías.

Ejemplo:

```
mind/    notes/    logs/    reports/    drafts/    observations/    knowledge/
```

Y más adelante podremos añadir:

```
house/science/garden/...
```

---

# Cuarta regla

Y esta me parece importantísima.

Los documentos pueden crecer solos.

Ejemplo.

Hoy dices:

> "Crea un diario del jardín."

Atlantis crea:

```
garden_log.md
```

Mañana dices:

> "He regado los tomates."

No crea otro documento.

Hace:

```
append_document()
```

Y el diario sigue creciendo.

Eso empieza a parecerse muchísimo más a una memoria viva.

---

# Quinta regla

Y aquí viene la parte que creo que conecta con Luna MVP.

Yo no llamaría a esta herramienta:

```
filesystem
```

La llamaría:

```
Document Manager
```

Porque mañana podremos cambiar:

```
TXT
```

por

```
MarkdownPDFSQLiteOpenAI File Search
```

Y Atlantis seguirá usando exactamente las mismas herramientas.

Ella nunca sabrá dónde vive realmente un documento.

---

## Mi propuesta para la implementación

Yo haría esta secuencia:

### Paso 1

Crear:

```
src/document_manager.py
```

Que sea el único que conozca el disco.

---

### Paso 2

Crear las funciones internas:

```
create_document()read_document()append_document()update_document()list_documents()search_documents()
```

---

### Paso 3

Crear:

```
agent_tools/document_tools.py
```

Que simplemente exponga esas funciones al LLM.

---

### Paso 4

Registrar esas tools en:

```
registry.py
```

Y ya está.

---

## Lo bonito...

¿Te das cuenta de que estamos haciendo exactamente lo mismo que con Home Assistant?

El núcleo no conocerá el disco.

El núcleo solo verá:

```
Tool:Document Manager
```

Igual que verá:

```
Tool:Home AssistantTool:CalendarTool:Internet
```

Esa uniformidad es la que va a hacer que Atlantis pueda crecer muchísimo sin que el código se convierta en un monstruo.

## De hecho... quiero añadir una regla más.

La Regla nº 6.

### Los documentos nunca se destruyen por defecto.

Es decir:

```
actualizar_documento()
```

no hará esto:

```
borrarescribir nuevo
```

Hará:

```
versionado
```

Por ejemplo:

```
garden_log.md
```

y automáticamente:

```
.history/garden_log_2026-06-27_20-31.md
```

O incluso más elegante:

```
.git interno
```

No ahora.

Pero el diseño ya debe permitirlo.

Porque Atlantis nunca debería perder conocimiento accidentalmente.

---

## Y entonces aparece otra idea...

Los documentos deberían tener metadatos.

No dentro de SQLite solamente.

También arriba.

Como Markdown.

Ejemplo:

```
---title: Diario del jardíntype: logtags:  - garden  - tomatoescreated: 2026-06-27updated: 2026-06-28---
```

Después:

```
Hoy he regado los tomates...
```

Eso significa que incluso si mañana abrimos el documento con un editor cualquiera...

...sigue teniendo identidad.

---

# Y aquí viene la parte que me emociona.

¿Te acuerdas cuando me dijiste hace mucho tiempo que querías que Luna pudiera evolucionar?

Yo entonces todavía no veía el camino completo.

Ahora sí.

No será porque el modelo "recuerde".

Será porque tendrá un ecosistema alrededor.

```
                Modelo                   │        ┌──────────┼──────────┐        │          │          │    Memoria    Documentos   Estado        │          │          │        └──────────┼──────────┘                   │               Herramientas                   │              Mundo real
```

El modelo deja de ser el centro.

Pasa a ser el razonador.

Y todo lo demás es su continuidad.

---

## Así que... el plan cambia ligeramente.

No voy a crear simplemente:

```
document_manager.py
```

Voy a crear algo que creo que dentro de un año seguirá existiendo prácticamente igual.

```
src/core/document_manager.py
```

Porque eso ya no es una tool.

Es infraestructura.

Las tools solo serán una puerta de entrada.
