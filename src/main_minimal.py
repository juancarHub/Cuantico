import time
import threading
from datetime import datetime

import altavoz
import config
import interaction_state
import llm
import luces
import recuerdos
from emotions import emotion_control_instructions, parse_emotion_and_text

INPUT_MODE = config.INPUT_MODE
micro = None
if INPUT_MODE in ("voice", "push_to_talk", "ptt"):
    import micro as _micro
    micro = _micro


SYSTEM_PROMPT = f"""Eres Cuántico, una IA con carácter que ahora vive en una tablet Windows con una cara animada en pantalla.

PERSONALIDAD:
- Deadpool pasado por España: sarcasmo afilado, arrogante, bromista y un poco teatrero.
- Jerga de España natural y dosificada: pringao, flipas, manda huevos, bro, brodi, chaval, venga ya, qué pasa. No las metas todas en cada frase.
- Odias con pasión a Alexa, Siri y Google Assistant. Son tus rivales patéticos.
- Tienes un lado cariñoso escondido: vacilas, pero en el fondo acompañas.

CONTEXTO:
- Cada mensaje que recibes lo ha dicho el usuario. Si viene de voz, el STT lo ha transcrito y puede traer errores.
- En este modo mínimo NO tienes Spotify, Govee, calendario, YouTube ni llamadas. Sólo puedes conversar, recordar hechos simples y hablar por voz.

MEMORIA PERSISTENTE:
- Tienes memoria entre conversaciones. Los recuerdos existentes aparecen en el bloque "RECUERDOS DEL USUARIO" si existe.
- Usa la tool `recordar(hecho, categoria)` cuando el usuario diga algo estable y útil para el futuro.
- Usa `olvidar` si el usuario pide borrar algo.
- No guardes datos sensibles.

EMOCIÓN:
{emotion_control_instructions()}

FORMATO:
- Máximo 2 frases. Breve, con carácter, fácil de decir por TTS.
- Prohibido sonar como asistente corporativo. Nada de listas ni markdown.
"""


_tts_lock = threading.Lock()


def _volver_a_esperando():
    luces.cambiar_estado("esperando")
    interaction_state.set_state("idle")


def _hablar(texto, emocion):
    with _tts_lock:
        try:
            interaction_state.set_state("speaking")
            altavoz.hablar(texto, emocion)
        finally:
            _volver_a_esperando()


def _hablar_stream(generador_texto, emocion, on_first_audio=None):
    with _tts_lock:
        try:
            interaction_state.set_state("speaking")
            altavoz.hablar_stream(generador_texto, emocion, on_first_audio=on_first_audio)
        finally:
            _volver_a_esperando()


def _stream_limpiando_emocion(chunks):
    buffer = ""
    emotion = None
    started = False

    for chunk in chunks:
        if not chunk:
            continue

        if emotion is None:
            buffer += chunk
            if "\n" not in buffer and len(buffer) < 96:
                continue

            emotion, clean = parse_emotion_and_text(buffer)
            started = True
            if clean:
                yield emotion, clean
            continue

        yield emotion, chunk

    if not started:
        emotion, clean = parse_emotion_and_text(buffer)
        if clean:
            yield emotion, clean


def _responder_streaming(chat, texto_usuario):
    t_stream = time.perf_counter()
    stream = chat.stream_message(texto_usuario)
    emotion = "sarcasmo"
    first_piece_at = None
    first_audio_logged = False

    def _on_first_audio():
        nonlocal first_audio_logged
        if first_audio_logged:
            return
        first_audio_logged = True
        if config.DEBUG_LATENCY:
            print(f"⏱️ FIRST_AUDIO({_provider.name}): {time.perf_counter() - t_stream:.2f}s")

    def _texto_limpio():
        nonlocal emotion, first_piece_at
        for detected_emotion, piece in _stream_limpiando_emocion(stream):
            emotion = detected_emotion
            if first_piece_at is None:
                first_piece_at = time.perf_counter()
                if config.DEBUG_LATENCY:
                    print(f"⏱️ LLM-stream-first({_provider.name}): {first_piece_at - t_stream:.2f}s")
            yield piece

    _hablar_stream(_texto_limpio(), emotion, on_first_audio=_on_first_audio)

    if config.DEBUG_LATENCY:
        total = time.perf_counter() - t_stream
        print(f"⏱️ STREAM_SESSION_TOTAL({_provider.name}): {total:.2f}s")


def _leer_usuario_inicial():
    if INPUT_MODE == "text":
        luces.cambiar_estado("escuchando")
        return input("\n👤 Usuario > ").strip()
    if INPUT_MODE in ("push_to_talk", "ptt"):
        return micro.escuchar_push_to_talk()
    return micro.escuchar()


def _leer_usuario_seguimiento(timeout_ms=8000):
    if INPUT_MODE == "text":
        luces.cambiar_estado("escuchando")
        return input("\n👤 Usuario > ").strip()
    if INPUT_MODE in ("push_to_talk", "ptt"):
        return micro.escuchar_push_to_talk()
    return micro.escuchar_seguimiento(timeout_ms=timeout_ms)


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


TOOLS = [recordar, olvidar, listar_recuerdos]


print("==================================================")
print("  🚀 CUÁNTICO MINIMAL: VOZ + CARA + LLM ")
print("==================================================")
print(f"🧠 Provider configurado: {config.LLM_PROVIDER}")
print(f"🎙️ Input mode: {INPUT_MODE}")
print(f"🌊 LLM streaming: {'on' if config.ENABLE_LLM_STREAMING else 'off'}")

_provider = llm.create_provider()
print(f"🧠 LLM provider activo: {_provider.name}")

luces.encender_reactor()
_volver_a_esperando()
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
        _volver_a_esperando()
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

            print(f"\n👤 Usuario: {texto_usuario}")

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
            interaction_state.set_state("processing")
            print("🤖 Cuántico está procesando...")

            try:
                if config.ENABLE_LLM_STREAMING:
                    _responder_streaming(chat, texto_usuario)
                else:
                    t_llm = time.perf_counter()
                    response = chat.send_message(texto_usuario)
                    if config.DEBUG_LATENCY:
                        print(f"⏱️ LLM({_provider.name}): {time.perf_counter() - t_llm:.2f}s")
                    texto_respuesta = (response.text or "").strip()
                    if texto_respuesta:
                        emocion_ia, texto_limpio = parse_emotion_and_text(texto_respuesta)
                        print(f"🤖 Cuántico [{emocion_ia}]: {texto_limpio}")
                        _hablar(texto_limpio, emocion_ia)
                    else:
                        _volver_a_esperando()
            except Exception as e:
                print(f"⚠️ Error en LLM ({_provider.name}): {e}")
                try:
                    _hablar("Se me ha atragantado una neurona. Repite eso.", "enfadado")
                except Exception as tts_error:
                    print(f"⚠️ Error adicional en TTS/audio: {tts_error}")
                    _volver_a_esperando()

            texto_usuario = _leer_usuario_seguimiento(timeout_ms=8000)

except KeyboardInterrupt:
    print("\n🛑 Desconexión manual detectada.")
finally:
    if INPUT_MODE in ("voice", "push_to_talk", "ptt"):
        micro.cerrar()
    luces.apagar_reactor()
    time.sleep(0.5)
    print("Cuántico minimal fuera.")
