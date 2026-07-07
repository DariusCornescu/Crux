"""Two-stage voice-note extraction (backlog feature 1, overnight Phase 1).

Stage 1: deterministic bilingual (RO/EN) keyword + regex tables — fast, offline.
Stage 2: LLM fallback via app.llm for long/ambiguous transcripts. When no
provider is configured, extraction stays deterministic (best effort) so the
feature works fully offline.
"""
import json
import logging
import re
import unicodedata

from app import llm

logger = logging.getLogger(__name__)

CONFIDENT_MAX_WORDS = 25

VOICE_EXTRACT_PROMPT = """You extract structured training data from an athlete's
short voice note (Romanian, English, or mixed). Reply with a one-sentence neutral
summary, then a fenced ```json block with EXACTLY these keys:
{"perceived_effort": int 1-10 or null, "session_type": one of
["sprint","tempo","easy_run","hike","ruck","strength"] or null,
"notes": short subjective summary string or null,
"symptoms": [strings like "heavy_legs","fatigue","strong","soreness"],
"terrain": [strings like "ice","snow","mud","wind"]}
Do not invent values not supported by the transcript."""

_RPE_RE = re.compile(r"\b(?:rpe|efort|effort)\s*:?\s*(\d{1,2})\b")
_RPE_SLASH_RE = re.compile(r"\b([1-9]|10)\s*/\s*10\b")

# Ordered — first match wins; more specific entries first ("ruck" before "hike"
# so "tura cu rucsac" classifies as ruck). Keys are diacritic-stripped lowercase.
_SESSION_KEYWORDS: list[tuple[str, str]] = [
    ("rucsac", "ruck"),
    ("ruck", "ruck"),
    ("sprint", "sprint"),          # also matches "sprinturi"
    ("tempo", "tempo"),
    ("alergare usoara", "easy_run"),
    ("easy run", "easy_run"),
    ("drumetie", "hike"),
    ("hike", "hike"),
    ("tura", "hike"),
    ("forta", "strength"),
    ("strength", "strength"),
]

_SYMPTOMS = {
    "heavy legs": "heavy_legs", "picioare grele": "heavy_legs",
    "tired": "fatigue", "obosit": "fatigue",
    "great": "strong", "puternic": "strong", "strong": "strong",
    "sore": "soreness", "dureri": "soreness",
}

_TERRAIN = {
    "ice": "ice", "gheata": "ice",
    "snow": "snow", "zapada": "snow",
    "mud": "mud", "noroi": "mud",
    "wind": "wind", "vant": "wind",
}


def _norm(text: str) -> str:
    """Lowercase + strip diacritics so RO text matches ASCII keyword tables."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _kw(needle: str, haystack: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(needle)}", haystack) is not None


def _analyze(transcript: str, lang: str | None) -> dict:
    """Best-effort deterministic pass — always returns a full result dict."""
    norm = _norm(transcript)

    rpe = None
    m = _RPE_RE.search(norm) or _RPE_SLASH_RE.search(norm)
    if m:
        value = int(m.group(1))
        rpe = value if 1 <= value <= 10 else None

    session_type = next((t for k, t in _SESSION_KEYWORDS if _kw(k, norm)), None)
    symptoms = sorted({v for k, v in _SYMPTOMS.items() if _kw(k, norm)})
    terrain = sorted({v for k, v in _TERRAIN.items() if _kw(k, norm)})

    return {"perceived_effort": rpe, "session_type": session_type, "notes": None,
            "symptoms": symptoms, "terrain": terrain, "method": "deterministic"}


def _deterministic(transcript: str, lang: str | None = None) -> dict | None:
    """Return the result only when confidently structured, else None (→ LLM)."""
    result = _analyze(transcript, lang)
    found = result["perceived_effort"] is not None or result["session_type"] or result["symptoms"]
    if found and len(transcript.split()) <= CONFIDENT_MAX_WORDS:
        return result
    return None


def _llm(transcript: str, lang: str | None = None) -> dict:
    text = llm.complete(
        system=VOICE_EXTRACT_PROMPT,
        messages=[{"role": "user", "content": transcript}],
        max_tokens=400,
    )
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        raise ValueError("no fenced json block in LLM extraction reply")
    data = json.loads(match.group(1))
    return {
        "perceived_effort": data.get("perceived_effort"),
        "session_type": data.get("session_type"),
        "notes": data.get("notes"),
        "symptoms": data.get("symptoms") or [],
        "terrain": data.get("terrain") or [],
        "method": "llm",
    }


def extract(transcript: str, lang: str | None = None) -> dict:
    confident = _deterministic(transcript, lang)
    if confident is not None:
        return confident
    if llm.is_configured():
        try:
            return _llm(transcript, lang)
        except Exception as e:  # unparseable/failed LLM → keep the feature alive
            logger.warning("LLM extraction failed (%s) — using deterministic best effort", e)
    return _analyze(transcript, lang)
