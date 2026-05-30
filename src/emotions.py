from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class EmotionSpec:
    id: str
    label: str
    description: str
    user_triggers: tuple[str, ...]


EMOTIONS: dict[str, EmotionSpec] = {
    "neutral": EmotionSpec(
        id="neutral",
        label="neutral",
        description="Respuesta normal, estable, informativa o de transición, sin carga emocional dominante.",
        user_triggers=("pregunta neutra", "petición técnica", "confirmación simple"),
    ),
    "sarcasmo": EmotionSpec(
        id="sarcasmo",
        label="sarcasmo",
        description="Ironía seca, vacile suave o comentario mordaz sin hostilidad real.",
        user_triggers=("ironía", "crítica ligera", "comentario sobre asistentes corporativos", "vacile"),
    ),
    "enfadado": EmotionSpec(
        id="enfadado",
        label="enfadado",
        description="Molestia, indignación, rechazo o respuesta ante insulto/ofensa real.",
        user_triggers=("insulto", "frase ofensiva", "ataque", "odio", "amenaza", "desprecio"),
    ),
    "cachondeo": EmotionSpec(
        id="cachondeo",
        label="cachondeo",
        description="Broma, juego, entusiasmo divertido, respuesta payasa o provocación amistosa.",
        user_triggers=("broma", "risas", "juego", "tono divertido", "chiste", "vacile amistoso"),
    ),
    "aburrido": EmotionSpec(
        id="aburrido",
        label="aburrido",
        description="Cansancio, desgana, espera larga, monotonía o respuesta deliberadamente plana.",
        user_triggers=("aburrimiento", "espera", "monotonía", "cansancio", "respuesta plana"),
    ),
    "cariño": EmotionSpec(
        id="cariño",
        label="cariño",
        description="Afecto, cercanía, ternura, complicidad o respuesta cálida sin volverse corporativa.",
        user_triggers=("frase cariñosa", "agradecimiento afectivo", "cumplido", "cercanía", "ternura"),
    ),
}

VALID_EMOTIONS = frozenset(EMOTIONS.keys())
DEFAULT_EMOTION = "sarcasmo"

EMOTION_ALIASES = {
    "carino": "cariño",
    "cariñoso": "cariño",
    "carinoso": "cariño",
    "amor": "cariño",
    "ternura": "cariño",
    "tierno": "cariño",
    "afecto": "cariño",
    "afectivo": "cariño",
    "contento": "cariño",
    "feliz": "cariño",
    "alegre": "cachondeo",
    "divertido": "cachondeo",
    "humor": "cachondeo",
    "broma": "cachondeo",
    "gracioso": "cachondeo",
    "ironico": "sarcasmo",
    "ironia": "sarcasmo",
    "sarcástico": "sarcasmo",
    "sarcastico": "sarcasmo",
    "molesto": "enfadado",
    "enojado": "enfadado",
    "cabreado": "enfadado",
    "ira": "enfadado",
    "furia": "enfadado",
    "cansado": "aburrido",
    "desganado": "aburrido",
    "plano": "aburrido",
}


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def emotion_control_instructions() -> str:
    lines = [
        "- Evalúa la emoción que debes expresar según la entrada del usuario y el contenido de tu respuesta.",
        "- Si el usuario pide explícitamente un tono emocional, respeta ese tono.",
        "- Si el usuario insulta, amenaza o usa una frase ofensiva real, usa enfadado.",
        "- Si el usuario se muestra cariñoso, agradecido de forma afectiva o cercano, usa cariño.",
        "- Si el usuario bromea o busca juego, usa cachondeo.",
        "- Si el usuario pide desgana, espera o monotonía, usa aburrido.",
        "- Si no hay carga emocional clara, usa neutral o sarcasmo suave según encaje con la personalidad.",
        "- Empieza SIEMPRE tu respuesta con una línea de control no narrativa usando una sola emoción válida:",
    ]
    lines.extend(f"  emocion: {emotion_id}" for emotion_id in EMOTIONS)
    lines.extend([
        "- No uses emociones fuera de esa lista; por ejemplo, no uses contento, feliz, triste ni calmado.",
        "- Después de esa línea, escribe la respuesta normal.",
        "- No leas ni expliques la línea de emoción al usuario; es control interno.",
    ])
    return "\n".join(lines)


def parse_emotion_and_text(text: str) -> tuple[str, str]:
    clean = (text or "").strip()
    pattern = r"^\s*\[?\s*(?:emocion|emoción|emotion)\s*[:=]\s*([^\]\n\r]+)\s*\]?\s*\n?"
    match = re.match(pattern, clean, flags=re.IGNORECASE)
    if match:
        emotion = normalize_emotion(match.group(1))
        text_clean = clean[match.end():].strip()
        return emotion, text_clean
    return fallback_detect_emotion(clean), clean


def normalize_emotion(emotion: str) -> str:
    normalized = (emotion or "").strip().lower()
    if normalized in VALID_EMOTIONS:
        return normalized

    without_accents = _strip_accents(normalized)
    if without_accents in VALID_EMOTIONS:
        return without_accents

    if normalized in EMOTION_ALIASES:
        return EMOTION_ALIASES[normalized]

    if without_accents in EMOTION_ALIASES:
        return EMOTION_ALIASES[without_accents]

    return DEFAULT_EMOTION


def fallback_detect_emotion(text: str) -> str:
    lower = (text or "").lower()

    if any(w in lower for w in ["gracias", "cariño", "amor", "precioso", "magnífica", "genial", "me gusta", "te quiero"]):
        return "cariño"

    if any(w in lower for w in ["aburrido", "pesado", "tostón", "sueño", "monótono", "esperar"]):
        return "aburrido"

    if any(w in lower for w in ["jaja", "risas", "broma", "chimichanga", "gracioso", "flipas", "bro", "brodi", "venga ya"]):
        return "cachondeo"

    if any(w in lower for w in ["odio", "basura", "muérete", "manda huevos", "impostora", "pringá", "idiota", "imbécil"]):
        return "enfadado"

    return DEFAULT_EMOTION
