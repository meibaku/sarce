"""Reviewer payloads stay blinded while qualification metrics remain visible."""

from pathlib import Path

from app.services.learning_review import reviewer_view

MIGRATION = Path(__file__).parents[3] / "supabase" / "migrations" / "20261027000000_atomic_pattern_reviews.sql"


def test_reviewer_view_never_exposes_other_votes_or_adjudication():
    view = reviewer_view({
        "id": "pattern", "position_fen": "fen", "label": "positive",
        "target": {"squares": ["e4"]}, "verification": {"epLoss": 0.2},
        "family_key": "family", "detector_version": 1, "stockfish_version": "18",
        "analysis_nodes": 1_500_000, "review_status": "candidate",
        "review_annotations": [{"reviewer": "other", "decision": "approve"}],
    })
    assert view["proposedLabel"] == "positive"
    assert "review_annotations" not in view
    assert "review_status" not in view


def test_reviewer_view_includes_versioned_evidence_for_an_informed_vote():
    view = reviewer_view({
        "id": "pattern", "position_fen": "fen", "label": "near_miss",
        "target": {}, "verification": {"relation": "recapture"}, "family_key": "family",
        "detector_version": 3, "stockfish_version": "18", "analysis_nodes": 1_500_000,
    })
    assert view["detectorVersion"] == 3
    assert view["analysisNodes"] == 1_500_000


def test_review_append_is_locked_and_rejects_duplicate_reviewers():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "for update" in sql
    assert "reviewer already annotated this pattern" in sql
    assert "revoke all on function public.append_pattern_review_annotation" in sql
