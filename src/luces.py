"""Fachada compatible para el sistema visual de Cuántico.

Mantiene la API histórica (`cambiar_estado`, `encender_reactor`, etc.)
pero delega en un backend seleccionable según plataforma.
"""

from display import create_display

_display = create_display()


def cambiar_estado(nuevo_estado):
    _display.set_state(nuevo_estado)


def encender_reactor():
    _display.start()


def apagar_reactor():
    _display.stop()
