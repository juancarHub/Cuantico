Añadido:

```
src/core/__init__.pysrc/core/document_manager.py
```

Este primer `document_manager` ya trae la base importante:

```
✔ workspace sandbox en mind/✔ índice SQLite en mind/.index/documents.db✔ carpetas iniciales:  notes/  logs/  reports/  drafts/  observations/  knowledge/  prompt_drafts/  .history/✔ documentos Markdown/TXT/LOG permitidos✔ front matter YAML✔ crear_documento()✔ leer_documento()✔ anexar_documento()✔ actualizar_documento()✔ listar_documentos()✔ buscar_documentos()✔ versionado antes de anexar/actualizar✔ bloqueo de rutas fuera del workspace
```

La regla nueva también ha quedado dentro:

```
actualizar/anexar↓guarda copia previa en mind/.history/
```

Siguiente paso: exponer esto al modelo como tools en:

```
src/agent_tools/document_tools.py
```

y después registrarlo en:

```
src/agent_tools/registry.py
```
