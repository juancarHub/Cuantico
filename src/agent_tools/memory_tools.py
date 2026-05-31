import recuerdos


def recordar(hecho: str, categoria: str = "") -> str:
    rid = recuerdos.añadir(hecho, categoria)
    return f"ok: recordado con id {rid}" if rid else "fallo: no se pudo guardar"


def olvidar(coincidencia: str) -> str:
    n = recuerdos.borrar_por_coincidencia(coincidencia)
    return f"ok: olvidados {n} recuerdo(s)" if n else "fallo: no encontré recuerdo con eso"


def listar_recuerdos() -> str:
    items = recuerdos.listar(50)
    if not items:
        return "no tengo recuerdos guardados todavía"
    return " | ".join(f"{r['texto']}" for r in items[:20])


def build_memory_tools() -> list:
    return [recordar, olvidar, listar_recuerdos]
