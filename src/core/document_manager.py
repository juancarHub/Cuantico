from __future__ import annotations

import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import config


WORKSPACE_DIR = Path(getattr(config, "ATLANTIS_WORKSPACE_DIR", Path(config.STATE_DIR).parent / "mind")).resolve()
INDEX_DB = WORKSPACE_DIR / ".index" / "documents.db"
ALLOWED_EXTENSIONS = {".md", ".txt", ".log"}
DEFAULT_CATEGORY = "notes"
DEFAULT_EXTENSION = ".md"

_conn: sqlite3.Connection | None = None


def inicializar() -> None:
    """Inicializa el workspace documental y su índice."""
    global _conn
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    for carpeta in ("notes", "logs", "reports", "drafts", "observations", "knowledge", "prompt_drafts", ".index", ".history"):
        (WORKSPACE_DIR / carpeta).mkdir(parents=True, exist_ok=True)

    _conn = sqlite3.connect(str(INDEX_DB), check_same_thread=False)
    _conn.execute(
        """CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            tags TEXT DEFAULT '',
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    _conn.commit()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        inicializar()
    assert _conn is not None
    return _conn


def _slug(texto: str) -> str:
    texto = (texto or "documento").strip().lower()
    texto = re.sub(r"[^a-z0-9áéíóúñü]+", "-", texto, flags=re.IGNORECASE)
    texto = texto.strip("-") or "documento"
    return texto[:80]


def _normalizar_categoria(categoria: str | None) -> str:
    categoria = (categoria or DEFAULT_CATEGORY).strip().strip("/\\") or DEFAULT_CATEGORY
    categoria = re.sub(r"[^a-zA-Z0-9_\-/áéíóúñü]+", "-", categoria)
    categoria = categoria.replace("\\", "/")
    partes = [p for p in categoria.split("/") if p not in ("", ".", "..")]
    return "/".join(partes) if partes else DEFAULT_CATEGORY


def _normalizar_tags(tags: str | list[str] | None) -> str:
    if isinstance(tags, list):
        return ",".join(t.strip() for t in tags if str(t).strip())
    return (tags or "").strip()


def _resolver_ruta_relativa(ruta_relativa: str) -> Path:
    ruta = (ruta_relativa or "").strip().replace("\\", "/").lstrip("/")
    if not ruta:
        raise ValueError("ruta vacía")
    p = (WORKSPACE_DIR / ruta).resolve()
    if WORKSPACE_DIR not in p.parents and p != WORKSPACE_DIR:
        raise ValueError("ruta fuera del workspace documental")
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"extensión no permitida: {p.suffix}")
    return p


def _ruta_para_nuevo_documento(titulo: str, categoria: str | None, extension: str | None = None) -> Path:
    categoria_ok = _normalizar_categoria(categoria)
    ext = (extension or DEFAULT_EXTENSION).lower().strip()
    if not ext.startswith("."):
        ext = "." + ext
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"extensión no permitida: {ext}")

    base_dir = (WORKSPACE_DIR / categoria_ok).resolve()
    if WORKSPACE_DIR not in base_dir.parents and base_dir != WORKSPACE_DIR:
        raise ValueError("categoría fuera del workspace documental")
    base_dir.mkdir(parents=True, exist_ok=True)

    base_name = _slug(titulo)
    candidato = base_dir / f"{base_name}{ext}"
    n = 2
    while candidato.exists():
        candidato = base_dir / f"{base_name}-{n}{ext}"
        n += 1
    return candidato


def _front_matter(titulo: str, categoria: str, tags: str, descripcion: str, creado: str, actualizado: str) -> str:
    tags_yaml = "\n".join(f"  - {t.strip()}" for t in tags.split(",") if t.strip()) or "  []"
    return (
        "---\n"
        f"title: {titulo}\n"
        f"category: {categoria}\n"
        "tags:\n"
        f"{tags_yaml}\n"
        f"description: {descripcion}\n"
        f"created: {creado}\n"
        f"updated: {actualizado}\n"
        "---\n\n"
    )


def _rel(path: Path) -> str:
    return path.resolve().relative_to(WORKSPACE_DIR).as_posix()


def _registrar_indice(titulo: str, categoria: str, path: Path, tags: str, descripcion: str, creado: str, actualizado: str) -> int:
    conn = _ensure_conn()
    rel = _rel(path)
    existente = conn.execute("SELECT id, created_at FROM documents WHERE path=?", (rel,)).fetchone()
    if existente:
        conn.execute(
            "UPDATE documents SET title=?, category=?, tags=?, description=?, updated_at=? WHERE id=?",
            (titulo, categoria, tags, descripcion, actualizado, existente[0]),
        )
        conn.commit()
        return int(existente[0])

    cur = conn.execute(
        "INSERT INTO documents (title, category, path, tags, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (titulo, categoria, rel, tags, descripcion, creado, actualizado),
    )
    conn.commit()
    return int(cur.lastrowid or 0)


def _guardar_version(path: Path) -> None:
    if not path.exists():
        return
    rel = _rel(path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = WORKSPACE_DIR / ".history" / rel
    destino = destino.with_name(f"{destino.stem}_{stamp}{destino.suffix}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destino)


def crear_documento(titulo: str, contenido: str = "", categoria: str = DEFAULT_CATEGORY, tags: str | list[str] | None = None, descripcion: str = "") -> str:
    titulo = (titulo or "Documento sin título").strip()
    categoria_ok = _normalizar_categoria(categoria)
    tags_ok = _normalizar_tags(tags)
    ahora = _now()
    path = _ruta_para_nuevo_documento(titulo, categoria_ok)
    path.parent.mkdir(parents=True, exist_ok=True)
    texto = _front_matter(titulo, categoria_ok, tags_ok, descripcion or "", ahora, ahora) + (contenido or "").strip() + "\n"
    path.write_text(texto, encoding="utf-8")
    doc_id = _registrar_indice(titulo, categoria_ok, path, tags_ok, descripcion or "", ahora, ahora)
    return f"ok: documento creado id={doc_id} ruta={_rel(path)}"


def leer_documento(ruta: str, max_chars: int = 12000) -> str:
    path = _resolver_ruta_relativa(ruta)
    if not path.exists():
        return f"fallo: no existe el documento {ruta}"
    texto = path.read_text(encoding="utf-8", errors="replace")
    if len(texto) > max_chars:
        return texto[:max_chars] + f"\n\n[contenido truncado: {len(texto)} caracteres totales]"
    return texto


def anexar_documento(ruta: str, contenido: str, encabezado: str = "") -> str:
    path = _resolver_ruta_relativa(ruta)
    if not path.exists():
        return f"fallo: no existe el documento {ruta}"
    _guardar_version(path)
    ahora = _now()
    bloque = "\n"
    if encabezado.strip():
        bloque += f"\n## {encabezado.strip()}\n\n"
    else:
        bloque += f"\n## Entrada {ahora}\n\n"
    bloque += (contenido or "").strip() + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(bloque)
    _actualizar_timestamp_indice(path)
    return f"ok: contenido añadido a {_rel(path)}"


def actualizar_documento(ruta: str, contenido: str) -> str:
    path = _resolver_ruta_relativa(ruta)
    if not path.exists():
        return f"fallo: no existe el documento {ruta}"
    _guardar_version(path)
    path.write_text((contenido or "").strip() + "\n", encoding="utf-8")
    _actualizar_timestamp_indice(path)
    return f"ok: documento actualizado {_rel(path)}; versión previa guardada en .history"


def _actualizar_timestamp_indice(path: Path) -> None:
    conn = _ensure_conn()
    conn.execute("UPDATE documents SET updated_at=? WHERE path=?", (_now(), _rel(path)))
    conn.commit()


def listar_documentos(categoria: str = "", limite: int = 50) -> str:
    conn = _ensure_conn()
    if categoria.strip():
        key = _normalizar_categoria(categoria) + "%"
        filas = conn.execute(
            "SELECT id, title, category, path, tags, updated_at FROM documents WHERE category LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (key, limite),
        ).fetchall()
    else:
        filas = conn.execute(
            "SELECT id, title, category, path, tags, updated_at FROM documents ORDER BY updated_at DESC LIMIT ?",
            (limite,),
        ).fetchall()
    if not filas:
        return "no hay documentos registrados"
    return "\n".join(f"#{r[0]} {r[1]} [{r[2]}] ruta={r[3]} tags={r[4] or '-'} actualizado={r[5]}" for r in filas)


def buscar_documentos(consulta: str, limite: int = 20) -> str:
    conn = _ensure_conn()
    q = (consulta or "").strip().lower()
    if not q:
        return "fallo: consulta vacía"
    key = f"%{q}%"
    filas = conn.execute(
        "SELECT id, title, category, path, tags, description, updated_at FROM documents WHERE LOWER(title) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(description) LIKE ? OR LOWER(path) LIKE ? ORDER BY updated_at DESC LIMIT ?",
        (key, key, key, key, limite),
    ).fetchall()
    if not filas:
        return "no he encontrado documentos con esa consulta"
    return "\n".join(f"#{r[0]} {r[1]} [{r[2]}] ruta={r[3]} tags={r[4] or '-'} descripción={r[5] or '-'}" for r in filas)
