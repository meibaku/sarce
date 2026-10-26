"""Scheduler v2 timing and projection rebuild tests."""

from datetime import datetime, timedelta, timezone

from app.services.learning_state import rebuild_state

START = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)


def attempt(index: int, *, correct: bool, assistance: str = "independent", confidence: int = 4, novel: bool = True, phase: str = "learning") -> dict:
    return {
        "id": f"00000000-0000-4000-8000-{index:012d}",
        "enrollment_id": "10000000-0000-4000-8000-000000000001",
        "participant_key": "20000000-0000-4000-8000-000000000001",
        "concept_key": "piece_safety.hanging_piece",
        "family_key": "family-a",
        "phase": phase,
        "correct": correct,
        "assistance": assistance,
        "confidence": confidence,
        "novel": novel,
        "responded_at": (START + timedelta(days=index)).isoformat(),
    }


def test_retry_rules_do_not_treat_confidence_as_success():
    wrong = rebuild_state([attempt(1, correct=False, confidence=5)])[0]
    hinted = rebuild_state([attempt(1, correct=True, assistance="hinted", confidence=5)])[0]
    assert wrong["stage"] == hinted["stage"] == "retry"
    assert datetime.fromisoformat(wrong["due_at"]) == START + timedelta(days=2)
    assert wrong["independent_correct"] == 0


def test_novel_and_delayed_spacing_are_exact():
    low = rebuild_state([attempt(1, correct=True, confidence=2)])[0]
    novel = rebuild_state([attempt(1, correct=True, confidence=4)])[0]
    delayed = rebuild_state([attempt(1, correct=True, confidence=4, novel=False)])[0]
    assert datetime.fromisoformat(low["due_at"]) == START + timedelta(days=4)
    assert datetime.fromisoformat(novel["due_at"]) == START + timedelta(days=8)
    assert datetime.fromisoformat(delayed["due_at"]) == START + timedelta(days=29)


def test_rebuild_is_deterministic_and_ignores_fixed_assessments():
    newest = attempt(3, correct=True, novel=False)
    rows = rebuild_state([newest, attempt(2, correct=False), attempt(1, correct=True), attempt(4, correct=True, phase="day7")])
    assert len(rows) == 1
    assert rows[0]["last_attempt_id"] == newest["id"]
    assert rows[0]["stage"] == "delayed"
    assert rows[0]["independent_correct"] == 2

