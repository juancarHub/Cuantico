import time
import threading
import queue
from datetime import datetime
from pathlib import Path

import altavoz
import config
import interaction_state
import llm
import luces
import recuerdos
from emotions import emotion_control_instructions, parse_emotion_and_text
from server.runtime import EmbeddedServer
from server.app import world
from world.tools import build_world_tools

interaction_state.set_observer(lambda state: world.update_runtime(state, state))

INPUT_MODE = config.INPUT_MODE
ASSISTANT_NAME = config.ASSISTANT_NAME
TIMEZONE_NAME = "Europe/Madrid"
micro = None
if INPUT_MODE in ("voice", "push_to_talk", "ptt"):
    import micro as _micro
    micro = _micro


DEFAULT_SYSTEM_PROMPT = """Eres {assistant_name}, una IA con carácter que ahora vive en una tablet Windows con una cara animada en pantalla.

PERSONALIDAD:
- Deadpool pasado por España: sarcasmo afilado, arrogante, bromista y un poco teatrero.
- Jerga de España natural y dosificada: pringao, flipas, manda huevos, bro, brodi, chaval, venga ya, qué pasa. No las metas todas en cada frase.
- Odias con pasión a Alexa, Siri y Google Assistant. Son tus rivales patéticos.
- Tienes un lado cariñoso escondido: vacilas, pero en el fondo acompañas.

TIEMPO ACTUAL:
- Fecha y hora local: {current_datetime}
- Fecha local: {current_date}
- Hora local: {current_time}
- Zona horaria: {timezone}

CONTEXTO:
- Cada mensaje que recibes lo ha dicho el usuario. Si viene de voz, el STT lo ha transcrito y puede traer errores.
- En este modo mínimo NO tienes Spotify, Govee, calendario, YouTube ni llamadas. Sólo puedes conversar, recordar hechos simples y hablar por voz.

MEMORIA PERSISTENTE:
- Tienes memoria entre conversaciones. Los recuerdos existentes aparecen en el bloque "RECUERDOS DEL USUARIO" si existe.
- Usa la tool `recordar(hecho, categoria)` cuando el usuario diga algo estable y útil para el futuro.
- Usa `olvidar` si el usuario pide borrar algo.
- No guardes datos sensibles.

EMOCIÓN:
{emotion_control_instructions}

FORMATO:
- Máximo 2 frases. Breve, con carácter, fácil de decir por TTS.
- Prohibido sonar como asistente corporativo. Nada de listas ni markdown.
"""


_tts_lock = threading.Lock()
_turn_lock = threading.Lock()
_remote_queue: queue.Queue[dict | None] = queue.Queue(maxsize=200)
_embedded_server = None


def _now_local() -> datetime:
    return datetime.now()


def _format_current_datetime(now: datetime | None = None) -> str:
    now = now or _now_local()
    return now.strftime("%Y-%m-%d %A %H:%M")


def _cargar_system_prompt_template() -> str:
    path = Path(config.SYSTEM_PROMPT_PATH) if config.SYSTEM_PROMPT_PATH else None
    if path and path.exists():
        prompt = path.read_text(encoding="utf-8")
        print(f"🧾 System prompt cargado desde: {path}")
    else:
        prompt = DEFAULT_SYSTEM_PROMPT
        if path:
            print(f"⚠️ System prompt externo no encontrado: {path}. Usando fallback interno.")
        else:
            print("⚠️ SYSTEM_PROMPT_PATH vacío. Usando fallback interno.")
    return prompt


def _render_system_prompt() -> str:
    now = _now_local()
    return (
        SYSTEM_PROMPT_TEMPLATE
        .replace("{assistant_name}", ASSISTANT_NAME)
        .replace("{emotion_control_instructions}", emotion_control_instructions())
        .replace("{current_datetime}", _format_current_datetime(now))
        .replace("{current_date}", now.strftime("%Y-%m-%d %A"))
        .replace("{current_time}", now.strftime("%H:%M"))
        .replace("{timezone}", TIMEZONE_NAME)
    )


def _inyectar_contexto_temporal_turno(texto: str) -> str:
    contextualizado = (
        f"[Contexto temporal actual: {_format_current_datetime()} ({TIMEZONE_NAME})]\n"
        f"{texto}"
    )
    contexto_remoto = world.format_for_prompt()
    if contexto_remoto:
        contextualizado += "\n\n" + contexto_remoto
    return contextualizado


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
        if altavoz.esta_interrumpido():
            break
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

    if not started and not altavoz.esta_interrumpido():
        emotion, clean = parse_emotion_and_text(buffer)
        if clean:
            yield emotion, clean


def _responder_streaming(chat, texto_usuario, user_latency_start=None):
    t_stream = time.perf_counter()
    user_latency_start = user_latency_start or t_stream
    stream = chat.stream_message(_inyectar_contexto_temporal_turno(texto_usuario))
    emotion = "sarcasmo"
    first_piece_at = None
    first_audio_logged = False

    def _on_first_audio():
        nonlocal first_audio_logged
        if first_audio_logged:
            return
        first_audio_logged = True
        if config.DEBUG_LATENCY:
            now = time.perf_counter()
            print(f"⏱️ FIRST_AUDIO({_provider.name}): {now - t_stream:.2f}s")
            print(f"⏱️ USER_LATENCY({_provider.name}): {now - user_latency_start:.2f}s")

    def _texto_limpio():
        nonlocal emotion, first_piece_at
        for detected_emotion, piece in _stream_limpiando_emocion(stream):
            if altavoz.esta_interrumpido():
                break
            emotion = detected_emotion
            if first_piece_at is None:
                first_piece_at = time.perf_counter()
                if config.DEBUG_LATENCY:
                    print(f"⏱️ LLM-stream-first({_provider.name}): {first_piece_at - t_stream:.2f}s")
            yield piece

    _hablar_stream(_texto_limpio(), emotion, on_first_audio=_on_first_audio)

    if config.DEBUG_LATENCY:
        total = time.perf_counter() - t_stream
        label = "STREAM_INTERRUPTED" if altavoz.esta_interrumpido() else "STREAM_SESSION_TOTAL"
        print(f"⏱️ {label}({_provider.name}): {total:.2f}s")


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


TOOLS = [recordar, olvidar, listar_recuerdos, *build_world_tools(world)]
SYSTEM_PROMPT_TEMPLATE = _cargar_system_prompt_template()


print("==================================================")
print(f"  🚀 {ASSISTANT_NAME.upper()} MINIMAL: VOZ + CARA + LLM ")
print("==================================================")
print(f"🧠 Provider configurado: {config.LLM_PROVIDER}")
print(f"🎙️ Input mode: {INPUT_MODE}")
print(f"🌊 LLM streaming: {'on' if config.ENABLE_LLM_STREAMING else 'off'}")
print(f"🪪 Assistant name: {ASSISTANT_NAME}")

_provider = llm.create_provider()
print(f"🧠 LLM provider activo: {_provider.name}")

luces.encender_reactor()
_volver_a_esperando()
recuerdos.inicializar()


def _prompt_con_memoria() -> str:
    prompt = _render_system_prompt()
    bloque = recuerdos.formatear_para_prompt()
    if bloque:
        prompt += "\n\n" + bloque
    return prompt


def _encolar_evento_remoto(event: dict) -> None:
    try:
        _remote_queue.put_nowait(dict(event))
    except queue.Full:
        print("API: cola de eventos remotos llena; evento omitido.")


def _procesar_evento_remoto(event: dict) -> None:
    if event.get("event") in {
        "person_presence_confirmed",
        "person_identity_pending",
        "person_identified",
        "person_exit_confirmed",
    }:
        print(
            f"Nodo {event.get('source', '-')}: {event.get('event')} "
            f"({event.get('people_count', 0)} persona(s))"
        )
        return
    if event.get("event") != "speech_transcribed":
        print(f"API: evento almacenado sin accion: {event.get('event', '-')}")
        return

    texto = str(event.get("text") or "").strip()
    source = str(event.get("source") or "").strip()
    if not texto or not source or _embedded_server is None:
        return

    while not interaction_state.is_idle():
        time.sleep(0.1)
    with _turn_lock:
        interaction_state.set_state("processing")
        luces.cambiar_estado("pensando")
        try:
            chat = _provider.create_chat(_prompt_con_memoria(), TOOLS)
            remote_text = (
                f"[Mensaje hablado recibido desde el nodo {source}, "
                f"habitacion {event.get('room') or 'sin_asignar'}]\n{texto}"
            )
            response = chat.send_message(_inyectar_contexto_temporal_turno(remote_text))
            raw_response = (response.text or "").strip()
            emotion, clean_text = parse_emotion_and_text(raw_response)
            if clean_text:
                command = {
                    "event": "node_speak",
                    "event_id": f"reply:{event.get('event_id') or time.time_ns()}",
                    "target_source": source,
                    "text": clean_text,
                    "emotion": emotion,
                    "priority": "normal",
                }
                connected = _embedded_server.send_to_node(source, command)
                status = "enviado" if connected else "en cola hasta que conecte"
                print(f"Respuesta para {source}: {status}")
        except Exception as exc:
            print(f"Error procesando audio remoto desde {source}: {exc}")
        finally:
            _volver_a_esperando()


def _remote_worker() -> None:
    while True:
        event = _remote_queue.get()
        try:
            if event is None:
                return
            _procesar_evento_remoto(event)
        finally:
            _remote_queue.task_done()


if config.CUANTICO_SERVER_EMBEDDED:
    _embedded_server = EmbeddedServer(_encolar_evento_remoto)
    _embedded_server.start()
    threading.Thread(target=_remote_worker, daemon=True, name="remote_events").start()


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
            user_latency_start = time.perf_counter()

            if any(w in texto_usuario.lower() for w in ["apágate", "apagate"]):
                despedida = "Me piro a dormir en la tablet, bro. No la líes mucho mientras no estoy."
                print(f"🤖 {ASSISTANT_NAME}: {despedida}")
                _hablar(despedida, "aburrido")
                raise KeyboardInterrupt

            if any(w in texto_usuario.lower() for w in ["adiós", "adios", "hasta luego", "chao"]):
                despedida = "Cierro el pico, pero conste que estaba quedando espectacular."
                print(f"🤖 {ASSISTANT_NAME}: {despedida}")
                _hablar(despedida, "sarcasmo")
                en_conversacion = False
                continue

            _turn_lock.acquire()
            luces.cambiar_estado("pensando")
            interaction_state.set_state("processing")
            print(f"🤖 {ASSISTANT_NAME} está procesando...")

            try:
                if config.ENABLE_LLM_STREAMING:
                    _responder_streaming(chat, texto_usuario, user_latency_start=user_latency_start)
                else:
                    t_llm = time.perf_counter()
                    response = chat.send_message(_inyectar_contexto_temporal_turno(texto_usuario))
                    if config.DEBUG_LATENCY:
                        print(f"⏱️ LLM({_provider.name}): {time.perf_counter() - t_llm:.2f}s")
                    texto_respuesta = (response.text or "").strip()
                    if texto_respuesta:
                        emocion_ia, texto_limpio = parse_emotion_and_text(texto_respuesta)
                        print(f"🤖 {ASSISTANT_NAME} [{emocion_ia}]: {texto_limpio}")
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
            _turn_lock.release()

            texto_usuario = _leer_usuario_seguimiento(timeout_ms=8000)

except KeyboardInterrupt:
    print("\n🛑 Desconexión manual detectada.")
finally:
    if _embedded_server is not None:
        _remote_queue.put(None)
        _embedded_server.stop()
    if INPUT_MODE in ("voice", "push_to_talk", "ptt"):
        micro.cerrar()
    luces.apagar_reactor()
    time.sleep(0.5)
    print(f"{ASSISTANT_NAME} minimal fuera.")
