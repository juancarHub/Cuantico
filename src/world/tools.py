from __future__ import annotations

import json

from .store import WorldStore


def build_world_tools(world: WorldStore) -> list:
    def consultar_habitacion(nombre: str) -> str:
        """Consulta ocupacion, personas y ultima observacion de una habitacion."""
        state = world.room(nombre)
        return json.dumps(state, ensure_ascii=False) if state else "habitacion no conocida"

    def consultar_persona(nombre: str) -> str:
        """Consulta ubicacion actual y ultimo lugar donde se vio a una persona."""
        state = world.person(nombre)
        return json.dumps(state, ensure_ascii=False) if state else "persona no conocida"

    def consultar_mundo() -> str:
        """Consulta el estado actual de habitaciones, personas y Cuantico."""
        return json.dumps(world.snapshot(), ensure_ascii=False)

    return [consultar_habitacion, consultar_persona, consultar_mundo]
