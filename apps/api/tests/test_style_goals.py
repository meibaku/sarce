"""The fractional target contract and its custom-goal-preserving migration."""

from pathlib import Path

from app.services.style_goals import (
    SOLID_GOAL_MAX,
    SOLID_GOAL_MIN,
    TAL_GOAL_MAX,
    TAL_GOAL_MIN,
)

MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "supabase"
    / "migrations"
    / "20261025002000_fractional_style_goals.sql"
)


def test_canonical_fractional_bands():
    assert (TAL_GOAL_MIN, TAL_GOAL_MAX) == (0.2, 0.6)
    assert (SOLID_GOAL_MIN, SOLID_GOAL_MAX) == (0.0, 0.2)


def test_migration_only_rewrites_exact_legacy_defaults():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "where style_goal =" in sql
    assert "target_brilliant_min = 6 and target_brilliant_max = 10" in sql
    assert "target_brilliant_min set default 0.2" in sql
    assert "target_brilliant_max set default 0.6" in sql
