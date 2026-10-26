"""Server-scored, append-only Learning Evidence attempt contracts."""

from datetime import datetime, timezone

import pytest

from app.services.learning_attempts import prepare_attempt, score_response

NOW = datetime(2026, 10, 26, tzinfo=timezone.utc)
ENROLLMENT = {
    "id": "10000000-0000-4000-8000-000000000001",
    "participant_key": "20000000-0000-4000-8000-000000000001",
    "protocol_version": 1,
    "arm": "experimental",
    "withdrawn_at": None,
}
PATTERN = {
    "id": "30000000-0000-4000-8000-000000000001",
    "review_status": "approved",
    "concept_key": "piece_safety.hanging_piece",
    "family_key": "pin-on-file",
    "label": "positive",
    "position_key": "fen-key",
    "detector_version": 1,
    "target": {"squares": ["e4"], "noImmediateDanger": False},
}


def test_score_response_requires_exact_answer_shape():
    assert score_response(PATTERN["target"], {"square": "e4"}) is True
    assert score_response(PATTERN["target"], {"square": "d4"}) is False
    assert score_response({"squares": [], "noImmediateDanger": True}, {"noImmediateDanger": True}) is True
    assert score_response(PATTERN["target"], {"square": "e4", "noImmediateDanger": True}) is False


def test_attempt_snapshots_versions_assignment_and_item_identity():
    row = prepare_attempt(
        enrollment=ENROLLMENT,
        pattern=PATTERN,
        client_attempt_id="40000000-0000-4000-8000-000000000001",
        phase="baseline",
        response={"square": "e4"},
        assistance="independent",
        confidence=4,
        latency_ms=1200,
        novel=True,
        presented_at=NOW,
        responded_at=NOW,
    )
    assert row["correct"] is True
    assert row["participant_key"] == ENROLLMENT["participant_key"]
    assert row["protocol_version"] == row["scoring_version"] == 1
    assert row["family_key"] == "pin-on-file"


def test_withdrawn_or_unapproved_evidence_is_rejected():
    kwargs = dict(
        enrollment=ENROLLMENT, pattern=PATTERN, client_attempt_id="40000000-0000-4000-8000-000000000001",
        phase="baseline", response={"square": "e4"}, assistance="independent", confidence=4,
        latency_ms=100, novel=True, presented_at=NOW, responded_at=NOW,
    )
    with pytest.raises(ValueError, match="withdrawn"):
        prepare_attempt(**{**kwargs, "enrollment": {**ENROLLMENT, "withdrawn_at": NOW.isoformat()}})
    with pytest.raises(ValueError, match="approved"):
        prepare_attempt(**{**kwargs, "pattern": {**PATTERN, "review_status": "candidate"}})

