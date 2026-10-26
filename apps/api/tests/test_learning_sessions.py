"""Fixed Learning Evidence manifests and answer-safe delivery contracts."""

from collections import Counter
from pathlib import Path

import pytest

from app.services.learning_sessions import PHASE_COUNTS, label_quota, select_patterns

MIGRATION = Path(__file__).parents[3] / "supabase" / "migrations" / "20261026005000_learning_sessions.sql"


def patterns(per_label: int = 20) -> list[dict]:
    return [
        {"id": f"{label}-{index}", "label": label, "family_key": f"{label}-family-{index}"}
        for label in ("positive", "near_miss", "control")
        for index in range(per_label)
    ]


@pytest.mark.parametrize("phase,count", PHASE_COUNTS.items())
def test_every_phase_has_the_preregistered_fixed_count(phase: str, count: int):
    assert len(select_patterns(patterns(), count=count, used_families=set(), seed=phase)) == count


def test_assessments_are_label_balanced_and_family_isolated():
    selected = select_patterns(
        patterns(), count=18, used_families={"positive-family-0", "control-family-0"}, seed="participant",
    )
    assert Counter(row["label"] for row in selected) == Counter(label_quota(18))
    families = [row["family_key"] for row in selected]
    assert len(families) == len(set(families))
    assert not {"positive-family-0", "control-family-0"} & set(families)


def test_manifest_fails_closed_when_a_label_is_thin():
    with pytest.raises(ValueError, match="cannot satisfy"):
        select_patterns(patterns(per_label=2), count=18, used_families=set(), seed="thin")


def test_manifest_is_deterministic_for_a_recorded_seed():
    first = select_patterns(patterns(), count=9, used_families=set(), seed="fixed")
    second = select_patterns(list(reversed(patterns())), count=9, used_families=set(), seed="fixed")
    assert [row["id"] for row in first] == [row["id"] for row in second]


def test_migration_hides_answers_and_claims_next_item_under_lock():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "alter table public.learning_presentations enable row level security" in sql
    assert "revoke all on function public.next_learning_presentation" in sql
    assert "limit 1 for update" in sql
    returned = sql.split("return jsonb_build_object(", 1)[1].split(");", 1)[0]
    assert "target" not in returned
    assert "verification" not in returned
