"""Pre-session listening vs session quality (pure functions + endpoint)."""
from datetime import datetime, timedelta, timezone

from app.audio_priming import best_session_audio, priming_profile
from app.models import Activity, ActivityType, ListeningSession

T0 = datetime(2026, 6, 22, 9, 0, tzinfo=timezone.utc)


def _track(minutes_before_t0, valence, energy, tempo, offset_h=0):
    return ListeningSession(
        played_at=T0 + timedelta(hours=offset_h) - timedelta(minutes=minutes_before_t0),
        track_name="t", valence=valence, energy=energy, tempo=tempo)


def _sprint(id, best_split, offset_h=0):
    return Activity(id=id, source="manual", type=ActivityType.sprint,
                    start_time=T0 + timedelta(hours=offset_h), duration_s=3600,
                    splits=[best_split, best_split + 0.1])


def test_priming_profile_window():
    activity = _sprint(1, 7.0)
    listening = [
        _track(30, 0.8, 0.9, 170.0),   # inside 60-min window
        _track(90, 0.2, 0.1, 80.0),    # too early — outside window
        _track(-10, 0.5, 0.5, 120.0),  # after start — ignored
    ]
    profile = priming_profile(activity, listening)
    assert profile["n"] == 1
    assert profile["valence"] == 0.8
    assert profile["energy"] == 0.9
    assert profile["tempo"] == 170.0


def test_priming_profile_none_without_tracks():
    assert priming_profile(_sprint(1, 7.0), []) is None


def test_best_session_audio_splits_by_quality():
    fast = _sprint(1, 6.95, offset_h=0)     # best sprint — high-energy priming
    slow = _sprint(2, 7.30, offset_h=48)    # rest — low-energy priming
    listening = [
        _track(20, 0.9, 0.95, 175.0, offset_h=0),
        _track(20, 0.3, 0.20, 90.0, offset_h=48),
    ]
    out = best_session_audio([fast, slow], listening)
    assert out["n_best"] == 1 and out["n_rest"] == 1
    assert out["best"]["energy"] > out["rest"]["energy"]
    assert out["best"]["tempo"] == 175.0


def test_endpoint_and_chat_context(client, db):
    r = client.get("/insights/audio-priming")
    assert r.status_code == 200
    assert set(r.json()) >= {"best", "rest", "n_best", "n_rest"}

    from app.chat_service import build_context
    assert "audio_priming" in build_context(db)
