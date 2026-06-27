from .memory_tools import build_memory_tools


def build_tools() -> list:
    """Construye la lista de herramientas disponibles para el agente."""
    tools = []
    tools.extend(build_memory_tools())
    return tools
