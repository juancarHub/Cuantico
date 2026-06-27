from core import document_manager


def crear_documento(titulo: str, contenido: str = "", categoria: str = "notes", tags: str = "", descripcion: str = "") -> str:
    """Crea un documento persistente dentro del espacio mental de Atlantis."""
    try:
        return document_manager.crear_documento(titulo, contenido, categoria, tags, descripcion)
    except Exception as exc:
        return f"fallo: no pude crear el documento: {exc}"


def leer_documento(ruta: str, max_chars: int = 12000) -> str:
    """Lee un documento del espacio mental de Atlantis por su ruta relativa."""
    try:
        return document_manager.leer_documento(ruta, max_chars=max_chars)
    except Exception as exc:
        return f"fallo: no pude leer el documento: {exc}"


def anexar_documento(ruta: str, contenido: str, encabezado: str = "") -> str:
    """Añade contenido al final de un documento existente, guardando versión previa."""
    try:
        return document_manager.anexar_documento(ruta, contenido, encabezado)
    except Exception as exc:
        return f"fallo: no pude anexar al documento: {exc}"


def actualizar_documento(ruta: str, contenido: str) -> str:
    """Reemplaza el contenido de un documento existente, guardando versión previa."""
    try:
        return document_manager.actualizar_documento(ruta, contenido)
    except Exception as exc:
        return f"fallo: no pude actualizar el documento: {exc}"


def listar_documentos(categoria: str = "", limite: int = 50) -> str:
    """Lista documentos registrados en el índice documental."""
    try:
        return document_manager.listar_documentos(categoria, limite)
    except Exception as exc:
        return f"fallo: no pude listar documentos: {exc}"


def buscar_documentos(consulta: str, limite: int = 20) -> str:
    """Busca documentos por título, etiquetas, descripción o ruta."""
    try:
        return document_manager.buscar_documentos(consulta, limite)
    except Exception as exc:
        return f"fallo: no pude buscar documentos: {exc}"


def build_document_tools() -> list:
    document_manager.inicializar()
    return [
        crear_documento,
        leer_documento,
        anexar_documento,
        actualizar_documento,
        listar_documentos,
        buscar_documentos,
    ]
