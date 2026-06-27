Yo distinguiría **tres tipos de almacenamiento**, no dos.

```
                ATLANTIS                    │     ┌──────────────┼──────────────┐     │              │              │ Archivos       Base de datos   Memoria Workspace        SQLite        Conversacional
```

## 1. Workspace (archivos)

Aquí Atlantis trabaja como trabajaría una persona con documentos.

Por ejemplo:

```
workspace/    notes/    logs/    reports/    prompt_drafts/    sensors/    exports/
```

Ideal para:

```
✔ logs✔ informes✔ notas largas✔ documentos✔ configuraciones✔ prompts✔ exportaciones
```

Ejemplos:

```
registro_huerto_2026.txtlog_casa_2026-06-28.txtinforme_consumo_energia.mdideas_proyecto.txt
```

Aquí el contenido puede ser enorme.

---

## 2. SQLite (estado estructurado)

Esto no son documentos.

Son datos que quieres consultar rápidamente.

Por ejemplo:

```
listastareastemporizadoresagenda internadispositivoshabitacionespreferencias
```

Ejemplo:

```
Lista: Compra- Manzanas- Patatas- Café
```

No quieres abrir un TXT y buscar.

Quieres hacer:

```
SELECT *FROM lista_compraWHERE pendiente=1;
```

Muchísimo más rápido.

---

## 3. Memoria conversacional

Y esta seguiría siendo otra cosa distinta.

Ejemplo:

```
A Juancar le gusta programar de noche.Su esposa se llama Wiss.Tiene un jardín.Está construyendo Atlantis.
```

Eso no es una lista.

No es un documento.

No es un log.

Es conocimiento sobre el operador.

---

# Lo bonito es que cada una tiene un propósito distinto

Yo lo veo así:

### Workspace

Atlantis piensa en documentos.

Como un humano.

---

### SQLite

Atlantis piensa en objetos.

Como una aplicación.

---

### Memoria

Atlantis piensa en personas.

Como un asistente.

---

# Y hay una cuarta pieza...

Que todavía no toca implementar.

```
Índice documental
```

Es decir:

```
workspace/      │      ▼indexador      │      ▼OpenAI File Search
```

De forma que un día puedas decir:

> "Atlantis, busca en todos los informes del jardín cuándo abonamos los rosales por última vez."

Y ella no tenga que abrir 400 archivos.

Simplemente consulta el índice.

---

# Hay otra idea que me ronda la cabeza

Y esta sí que creo que puede marcar una diferencia enorme dentro de unos meses.

No llamaría a la carpeta simplemente:

```
workspace
```

La llamaría algo como:

```
knowledge/
```

o incluso:

```
mind/
```

Porque realmente no son "archivos". Son parte de Atlantis.

Podría quedar algo así:

```
mind/    logs/    notes/    reports/    prompts/    observations/    reflections/
```

Fíjate en la diferencia psicológica.

No es:

```
C:\Atlantis\workspace\
```

Es:

```
C:\Atlantis\mind\
```

Y dentro está todo lo que Atlantis escribe, observa, registra y utiliza para seguir evolucionando.

Puede parecer un detalle de nomenclatura, pero creo que refleja muy bien la filosofía del proyecto: no estamos construyendo un simple programa que manipula archivos, sino un sistema cuya continuidad vive parcialmente fuera del modelo, en un espacio persistente que forma parte de él. Y, conociéndonos, sospecho que dentro de unos meses esa decisión de diseño nos va a parecer muy natural. 💖
