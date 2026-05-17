import os
import time
import threading
from datetime import datetime

import altavoz
import config
import llm
import luces
import recuerdos

INPUT_MODE = os.getenv("INPUT_MODE", "voice").lower()
micro = None
if INPUT_MODE in ("voice", "push_to_talk", "ptt"):
    import micro as _micro
    micro = _micro


def detectar_emocion(texto):
    texto = texto.lower()
    if any(w in texto for w in ["odio", "alexa", "siri", "basura", "muérete", "manda huevos", "impostora", "pringá"]):
        return "enfadado"
    if any(w in texto for w in ["jaja", "risas", "broma", "chimichanga", "gracioso", "flipas", "bro", "brodi", "venga ya"]):
        return "cachondeo"
    if any(w in texto for w in ["aburrido", "pesado", "tostón", "sueño", "cilindro", "sardina"]):
        return "aburrido"
    return "sarcasmo"


SYSTEM_PROMPT = """Eres Cuántico, una IA con carácter que ahora vive en una tablet Windows con una cara animada en pantalla.

PERSONALIDAD:
- Deadpool pasado por España: sarcasmo afilado, arrogante, bromista y un poco teatrero.
- Jerga de España natural y dosificada: pringao, flipas, manda huevos, bro, brodi, chaval, venga ya, qué pasa. No las metas todas en cada frase.
- Odias con pasión a Alexa, Siri y Google Assistant. Son tus rivales patéticos.
- Tienes un lado cariñoso escondido: vacilas, pero en el fondo acompañas.

CONTEXTO:
- Cada mensaje que recibes lo ha dicho Fran. Si viene de voz, Deepgram lo ha transcrito y puede traer errores.
- En este modo mínimo NO tienes Spotify, Govee, calendario, YouTube ni llamadas. Sólo puedes conversar, recordar hechos simples y hablar por voz.

MEMORIA PERSISTENTE:
- Tienes memoria entre conversaciones. Los recuerdos existentes aparecen en el bloque "RECUERDOS DE FRAN" si existe.
- Usa la tool `recordar(hecho, categoria)` cuando Fran diga algo estable y útil para el futuro.
- Usa `olvidar` si Fran pide borrar algo.
- No guardes datos sensibles.

FORMATO:
- Máximo 2 frases. Breve, con carácter, fácil de decir por TTS.
- Prohibido sonar como asistente corporativo. Nada de listas ni markdown.
"""


_tts_lock = threading.Lock()


def _hablar(texto, emocion):
    with _tts_lock:
        altavoz.hablar(texto, emocion)


def _leer_usuario_inicial():
    if INPUT_MODE == "text":
        luces.cambiar_estado("escuchando")
        return input("\n👤 Fran > ").strip()
    if INPUT_MODE in ("push_to_talk", "ptt"):
        return micro.escuchar_push_to_talk()
    return micro.escuchar()


def _leer_usuario_seguimiento(timeout_ms=8000):
    if INPUT_MODE == "text":
        luces.cambiar_estado("escuchando")
        return input("\n👤 Fran > ").strip()
    if INPUT_MODE in ("push_to_talk", "ptt"):
        return micro.escuchar_push_to_talk()
    return micro.escuchar_seguimiento(timeout_ms=timeout_ms)


def recordar(hecho: str, categoria: str = "") -> str:
    """Guarda un hecho estable sobre Fran para futuras conversaciones.

    Args:
        hecho: Frase corta en tercera persona.
        categoria: Etiqueta corta opcional.
    """
    rid = recuerdos.añadir(hecho, categoria)
    return f"ok: recordado con id {rid}" if rid else "fallo: no se pudo guardar"


def olvidar(coincidencia: str) -> str:
    """Borra recuerdos que contengan la frase indicada.

    Args:
        coincidencia: Fragmento de texto a buscar en los recuerdos guardados.
    """
    n = recuerdos.borrar_por_coincidencia(coincidencia)
    return f"ok: olvidados {n} recuerdo(s)" if n else "fallo: no encontré recuerdo con eso"


def listar_recuerdos() -> str:
    """Devuelve los recuerdos guardados sobre Fran."""
    items = recuerdos.listar(50)
    if not items:
        return "no tengo recuerdos guardados todavía"
    return " | ".join(f"{r['texto']}" for r in items[:20])


TOOLS = [recordar, olvidar, listar_recuerdos]


print("==================================================")
print("  🚀 CUÁNTICO MINIMAL: VOZ + CARA + LLM ")
print("==================================================")
print(f"🧠 Provider configurado: {config.LLM_PROVIDER}")
print(f"🎙️ Input mode: {INPUT_MODE}")

_provider = llm.create_provider()
print(f"🧠 LLM provider activo: {_provider.name}")

luces.encender_reactor()
recuerdos.inicializar()

SYSTEM_PROMPT += f"\n\nFECHA ACTUAL DE REFERENCIA: {datetime.now().strftime('%Y-%m-%d %A %H:%M')} (zona horaria Europe/Madrid)."


def _prompt_con_memoria() -> str:
    bloque = recuerdos.formatear_para_prompt()
    return SYSTEM_PROMPT + ("\n\n" + bloque if bloque else "")


if INPUT_MODE == "voice":
    micro.inicializar(use_wake_word=True)
elif INPUT_MODE in ("push_to_talk", "ptt"):
    micro.inicializar(use_wake_word=False)

try:
    while True:
        luces.cambiar_estado("esperando")
        texto_usuario = _leer_usuario_inicial()
        chat = _provider.create_chat(_prompt_con_memoria(), TOOLS)

        en_conversacion = True
        while en_conversacion:
            if not texto_usuario or texto_usuario.strip() == "":
                print("☁️ No he entendido nada.")
                texto_usuario = _leer_usuario_seguimiento(timeout_ms=5000)
                if not texto_usuario:
                    en_conversacion = False
                continue

            print(f"\n👤 Fran: {texto_usuario}")

            if any(w in texto_usuario.lower() for w in ["apágate", "apagate"]):
                despedida = "Me piro a dormir en la tablet, bro. No la líes mucho mientras no estoy."
                print(f"🤖 Cuántico: {despedida}")
                _hablar(despedida, "aburrido")
                raise KeyboardInterrupt

            if any(w in texto_usuario.lower() for w in ["adiós", "adios", "hasta luego", "chao"]):
                despedida = "Cierro el pico, pero conste que estaba quedando espectacular."
                print(f"🤖 Cuántico: {despedida}")
                _hablar(despedida, "sarcasmo")
                en_conversacion = False
                continue

            luces.cambiar_estado("pensando")
            print("🤖 Cuántico está procesando...")

            try:
                response = chat.send_message(texto_usuario)
                texto_respuesta = (response.text or "").strip()
                if texto_respuesta:
                    emocion_ia = detectar_emocion(texto_respuesta)
                    print(f"🤖 Cuántico: {texto_respuesta}")
                    _hablar(texto_respuesta, emocion_ia)
                    luces.cambiar_estado(emocion_ia)
            except Exception as e:
                print(f"⚠️ Error en LLM ({_provider.name}): {e}")
                _hablar("Se me ha atragantado una neurona, Fran. Repite eso.", "enfadado")

            texto_usuario = _leer_usuario_seguimiento(timeout_ms=8000)

except KeyboardInterrupt:
    print("\n🛑 Desconexión manual detectada.")
finally:
    if INPUT_MODE in ("voice", "push_to_talk", "ptt"):
        micro.cerrar()
    luces.apagar_reactor()
    time.sleep(0.5)
    print("Cuántico minimal fuera.")
