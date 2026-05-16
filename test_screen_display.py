import os
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

os.environ["DISPLAY_BACKEND"] = "screen"

import luces

luces.encender_reactor()

for estado in [
    "esperando",
    "escuchando",
    "pensando",
    "sarcasmo",
    "cachondeo",
    "enfadado",
    "aburrido",
    "apagado",
]:
    print("Estado:", estado)
    luces.cambiar_estado(estado)
    time.sleep(3)

luces.apagar_reactor()