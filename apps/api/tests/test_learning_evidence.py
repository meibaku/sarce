"""Preregistered balanced-accuracy estimand and clustered uncertainty."""

import pytest

from app.services.learning_evidence import balanced_accuracy, participant_changes, primary_report


def item(person: str, arm: str, phase: str, label: str, correct: bool, assistance: str = "independent") -> dict:
    return {
        "participant_key": person,
        "arm": arm,
        "phase": phase,
        "item_label": label,
        "correct": correct,
        "assistance": assistance,
    }


def phase(person: str, arm: str, name: str, positive: bool, negative: bool) -> list[dict]:
    return [item(person, arm, name, "positive", positive) for _ in range(9)] + [
        item(person, arm, name, "control", negative) for _ in range(9)
    ]


def test_balanced_accuracy_requires_both_classes_and_independence():
    rows = [item("p", "experimental", "baseline", "positive", True), item("p", "experimental", "baseline", "control", True, "hinted")]
    assert balanced_accuracy(rows) == 0.5
    assert balanced_accuracy(rows[:1]) is None


def test_participant_changes_excludes_incomplete_followup():
    rows = phase("e1", "experimental", "baseline", False, True) + phase("e1", "experimental", "day7", True, True)
    rows += phase("e2", "experimental", "baseline", True, True)
    changes = participant_changes(rows)
    assert changes["experimental"] == [0.5]


def test_primary_report_is_deterministic_and_player_clustered():
    rows = []
    rows += phase("e1", "experimental", "baseline", False, True) + phase("e1", "experimental", "day7", True, True)
    rows += phase("e2", "experimental", "baseline", False, False) + phase("e2", "experimental", "day7", True, False)
    rows += phase("c1", "active_control", "baseline", False, True) + phase("c1", "active_control", "day7", False, True)
    rows += phase("c2", "active_control", "baseline", True, False) + phase("c2", "active_control", "day7", True, False)
    first = primary_report(rows, resamples=500, seed=7)
    assert first == primary_report(rows, resamples=500, seed=7)
    assert first["effectPercentagePoints"] == 50.0
    assert first["completeParticipants"] == {"experimental": 2, "activeControl": 2}
    assert first["bootstrap"]["unit"] == "participant"


def test_cross_arm_participant_is_rejected():
    rows = phase("p", "experimental", "baseline", True, True) + phase("p", "active_control", "day7", True, True)
    with pytest.raises(ValueError, match="more than one arm"):
        participant_changes(rows)

