"""Two-stage extraction: deterministic first, LLM fallback for long/ambiguous."""
from app import voice_extract


def test_deterministic_bilingual_short():
    out = voice_extract.extract("RPE 8, picioare grele după sprinturi")
    assert out["perceived_effort"] == 8
    assert "heavy_legs" in out["symptoms"]
    assert out["session_type"] == "sprint"
    assert out["method"] == "deterministic"


def test_deterministic_rpe_slash_form_and_terrain():
    out = voice_extract.extract("easy run 7/10, lots of mud and wind")
    assert out["perceived_effort"] == 7
    assert out["session_type"] == "easy_run"
    assert set(out["terrain"]) >= {"mud", "wind"}
    assert out["method"] == "deterministic"


def test_long_ambiguous_offline_stays_deterministic():
    # No provider key in the test env -> must NOT attempt the LLM; returns
    # best-effort deterministic even though confidence is low.
    transcript = (
        "so today honestly it started okay but then around the middle everything "
        "kind of fell apart and I am not sure whether it was the sleep or the food "
        "or just the accumulated load from the whole block to be honest"
    )
    out = voice_extract.extract(transcript)
    assert out["method"] == "deterministic"


def test_long_transcript_uses_llm_when_configured(monkeypatch):
    fixed = {"perceived_effort": 6, "session_type": "hike", "notes": "long day",
             "symptoms": ["fatigue"], "terrain": ["snow"], "method": "llm"}
    monkeypatch.setattr(voice_extract.llm, "is_configured", lambda: True)
    monkeypatch.setattr(voice_extract, "_llm", lambda transcript, lang: fixed)
    transcript = " ".join(["word"] * 40)
    out = voice_extract.extract(transcript)
    assert out == fixed


def test_confidence_gate_word_count():
    # Has a keyword but is long -> not "confident" -> (offline) best-effort deterministic
    transcript = "sprint " + " ".join(["filler"] * 30)
    out = voice_extract.extract(transcript)
    assert out["session_type"] == "sprint"
    assert out["method"] == "deterministic"
