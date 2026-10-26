"""Frozen LE2 outcome estimand and deterministic player-cluster bootstrap."""

from __future__ import annotations

import random
from collections import defaultdict
from statistics import mean

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20_261_026
FIXED_ASSESSMENT_ITEMS = 18


def analysis_rows(rows: list[dict]) -> list[dict]:
    """Fail closed to the snapshotted controlled cohort used by the preregistered estimand."""
    return [
        row for row in rows
        if row.get("analysis_eligible") is True and row.get("cohort") == "controlled"
    ]


def balanced_accuracy(rows: list[dict]) -> float | None:
    """Average positive sensitivity and negative specificity; assisted responses remain incorrect."""
    positive = [row for row in rows if row["item_label"] == "positive"]
    negative = [row for row in rows if row["item_label"] in {"near_miss", "control"}]
    if not positive or not negative:
        return None

    def success(row: dict) -> bool:
        return row.get("correct") is True and row.get("assistance") == "independent"

    return (mean(success(row) for row in positive) + mean(success(row) for row in negative)) / 2


def participant_changes(rows: list[dict]) -> dict[str, list[float]]:
    """Return complete baseline-to-day-7 changes by randomised arm."""
    rows = analysis_rows(rows)
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    arms: dict[str, str] = {}
    for row in rows:
        if row.get("phase") not in {"baseline", "day7"}:
            continue
        participant = str(row["participant_key"])
        grouped[(participant, row["phase"])].append(row)
        prior = arms.setdefault(participant, row["arm"])
        if prior != row["arm"]:
            raise ValueError("participant appears in more than one arm")
    changes: dict[str, list[float]] = {"experimental": [], "active_control": []}
    for participant, arm in arms.items():
        baseline_rows = grouped[(participant, "baseline")]
        day7_rows = grouped[(participant, "day7")]
        if len(baseline_rows) != FIXED_ASSESSMENT_ITEMS or len(day7_rows) != FIXED_ASSESSMENT_ITEMS:
            continue
        before = balanced_accuracy(baseline_rows)
        after = balanced_accuracy(day7_rows)
        if before is not None and after is not None:
            changes[arm].append(after - before)
    return changes


def _quantile(sorted_values: list[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    fraction = position - lower
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def primary_report(
    rows: list[dict], *, resamples: int = BOOTSTRAP_RESAMPLES, seed: int = BOOTSTRAP_SEED
) -> dict:
    """Estimate the preregistered difference-in-change and its player-level bootstrap interval."""
    if resamples < 100:
        raise ValueError("at least 100 bootstrap resamples are required")
    changes = participant_changes(rows)
    eligible = analysis_rows(rows)
    experimental, control = changes["experimental"], changes["active_control"]
    if not experimental or not control:
        raise ValueError("both arms need complete baseline and day-7 participants")
    effect = mean(experimental) - mean(control)
    rng = random.Random(seed)
    draws = sorted(
        mean(rng.choice(experimental) for _ in experimental) - mean(rng.choice(control) for _ in control)
        for _ in range(resamples)
    )
    included = {
        arm: len({str(row["participant_key"]) for row in eligible if row.get("arm") == arm})
        for arm in changes
    }
    item_denominators = {
        arm: {
            phase: sum(row.get("arm") == arm and row.get("phase") == phase for row in eligible)
            for phase in ("baseline", "day7")
        }
        for arm in changes
    }
    return {
        "estimand": "between-arm baseline-to-day7 balanced-accuracy change",
        "effectPercentagePoints": round(effect * 100, 3),
        "confidenceInterval95PercentagePoints": [
            round(_quantile(draws, 0.025) * 100, 3),
            round(_quantile(draws, 0.975) * 100, 3),
        ],
        "armChangePercentagePoints": {
            "experimental": round(mean(experimental) * 100, 3),
            "activeControl": round(mean(control) * 100, 3),
        },
        "completeParticipants": {"experimental": len(experimental), "activeControl": len(control)},
        "observedParticipants": {"experimental": included["experimental"], "activeControl": included["active_control"]},
        "assessmentItems": {
            "experimental": item_denominators["experimental"],
            "activeControl": item_denominators["active_control"],
        },
        "attempts": len(eligible),
        "excludedAttempts": len(rows) - len(eligible),
        "bootstrap": {"unit": "participant", "resamples": resamples, "seed": seed},
    }

