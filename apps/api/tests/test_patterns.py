"""LE2 pattern-bank contracts: explicit visibility, provenance and answer-safe client views."""

from pathlib import Path

import pytest

from app.services.patterns import prepare_candidate, serving_view

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
ROOT = Path(__file__).resolve().parents[3]


def candidate(**overrides):
    values = {
        "fen": START,
        "family_key": "start-shape",
        "visibility": "private",
        "owner_id": "00000000-0000-4000-8000-000000000001",
        "source_type": "own_game",
        "source_game_id": "10000000-0000-4000-8000-000000000001",
        "source_ply": 4,
        "label": "control",
        "target": {"answer": "nothing"},
        "verification": {"epLoss": 0.0},
        "stockfish_version": "Stockfish 18",
        "analysis_nodes": 1_500_000,
        "detector_version": 1,
    }
    values.update(overrides)
    return prepare_candidate(**values)


def test_candidate_normalizes_position_and_builds_stable_scope_key():
    first = candidate()
    second = candidate(fen=START.replace("0 1", "0 9"))
    assert first["position_fen"] == START
    assert first["position_key"] == second["position_key"]
    assert first["dedupe_key"] == second["dedupe_key"]
    assert len(first["dedupe_key"]) == 64


def test_personal_and_global_scope_are_explicit():
    with pytest.raises(ValueError, match="owner_id"):
        candidate(owner_id=None)
    with pytest.raises(ValueError, match="cannot have owner"):
        candidate(visibility="global")
    with pytest.raises(ValueError, match="own-game"):
        candidate(visibility="global", owner_id=None)
    shared = candidate(
        visibility="global", owner_id=None, source_type="curated", source_game_id=None, source_ply=None
    )
    assert shared["visibility"] == "global" and shared["owner_id"] is None


def test_serving_view_never_leaks_answer_or_verification():
    row = candidate()
    row["id"] = "p1"
    public = serving_view(row)
    assert public["id"] == "p1" and public["position_fen"] == START
    assert "target" not in public
    assert "verification" not in public
    assert "review_annotations" not in public
    assert "dedupe_key" not in public


def test_invalid_domain_values_and_unplayable_positions_fail_closed():
    with pytest.raises(ValueError, match="label"):
        candidate(label="mastered")
    with pytest.raises(ValueError, match="playable"):
        candidate(fen="8/8/8/8/8/8/8/8 w - - 0 1")
    with pytest.raises(ValueError, match="positive"):
        candidate(analysis_nodes=0)


def test_migration_enables_rls_without_client_grants():
    sql = (ROOT / "supabase" / "migrations" / "20261026000000_learning_pattern_instances.sql").read_text(encoding="utf-8").lower()
    assert "alter table public.pattern_instances enable row level security" in sql
    assert "grant select, insert, update, delete on public.pattern_instances to service_role" in sql
    assert "to authenticated" not in sql and "to anon" not in sql
    assert "visibility = 'private' and owner_id is not null" in sql
    assert "visibility = 'global' and owner_id is null" in sql
