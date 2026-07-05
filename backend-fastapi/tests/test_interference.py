"""Session-sequencing interference rules (pure functions) + knowledge-file sync."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.interference import detect
from app.models import Activity, ActivityType

T0 = datetime(2026, 6, 22, 8, 0, tzinfo=timezone.utc)


def _act(id, type_, hours_after=0, distance_m=None, vert=None):
    return Activity(id=id, source="manual", type=type_,
                    start_time=T0 + timedelta(hours=hours_after), duration_s=3600,
                    distance_m=distance_m, elevation_gain_m=vert)


def _codes(flags):
    return [f["code"] for f in flags]


def test_aerobic_blunts_sprint_fires_within_48h():
    flags = detect([
        _act(1, ActivityType.easy_run, 0, distance_m=14000),
        _act(2, ActivityType.sprint, 24),
    ])
    assert _codes(flags) == ["aerobic_blunts_sprint"]
    assert flags[0]["activity_ids"] == [1, 2]
    assert flags[0]["pattern_ref"]


def test_aerobic_blunts_sprint_respects_gap_and_threshold():
    # >48h gap → no flag
    assert detect([_act(1, ActivityType.easy_run, 0, distance_m=14000),
                   _act(2, ActivityType.sprint, 50)]) == []
    # short aerobic session → no flag
    assert detect([_act(1, ActivityType.easy_run, 0, distance_m=8000),
                   _act(2, ActivityType.sprint, 24)]) == []


def test_sprint_before_recovery_fires():
    flags = detect([
        _act(1, ActivityType.sprint, 0),
        _act(2, ActivityType.easy_run, 30, distance_m=15000),
    ])
    assert _codes(flags) == ["sprint_before_recovery"]
    assert flags[0]["activity_ids"] == [1, 2]


def test_sprint_before_recovery_needs_long_aerobic():
    assert detect([_act(1, ActivityType.sprint, 0),
                   _act(2, ActivityType.easy_run, 30, distance_m=6000)]) == []


def test_loaded_before_sprint_fires():
    flags = detect([
        _act(1, ActivityType.ruck, 0, vert=900),
        _act(2, ActivityType.sprint, 40),
    ])
    assert _codes(flags) == ["loaded_before_sprint"]


def test_loaded_before_sprint_needs_big_vert_and_window():
    assert detect([_act(1, ActivityType.ruck, 0, vert=500),
                   _act(2, ActivityType.sprint, 40)]) == []
    assert detect([_act(1, ActivityType.ruck, 0, vert=900),
                   _act(2, ActivityType.sprint, 72)]) == []


def test_knowledge_file_covers_all_pattern_refs():
    knowledge = Path("app/knowledge/concurrent_training.md").read_text(encoding="utf-8")
    assert knowledge.strip(), "knowledge file must not be empty"

    broad = [
        _act(1, ActivityType.easy_run, 0, distance_m=14000),
        _act(2, ActivityType.sprint, 24),
        _act(3, ActivityType.easy_run, 40, distance_m=15000),
        _act(4, ActivityType.ruck, 60, vert=900),
        _act(5, ActivityType.sprint, 80),
    ]
    flags = detect(broad)
    assert flags, "broad fixture should produce flags"

    heading_lines = [l.lower() for l in knowledge.splitlines() if l.startswith("#")]
    for ref in {f["pattern_ref"] for f in flags}:
        anchor = ref.split("#", 1)[1]
        assert any(anchor in line for line in heading_lines), f"missing heading for {anchor}"
