"""
Chaos validation maths — Chaos Lens M4 (docs/CHAOS_PLAN.md).

Pure helpers for scripts/validate_chaos.py: sampling buckets, the tuning / held-out
split, calibration tables, baselines and the clock multiplier. No engine, no I/O.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict

CLOCK_BUCKETS = ("<5s", "5-15s", "15s+")
RATING_BAND = 200


def rating_band(rating: int) -> int:
    """Lower edge of the 200-point band a rating falls in."""
    return (rating // RATING_BAND) * RATING_BAND


def clock_bucket(clock_ms: int | None) -> str | None:
    if clock_ms is None:
        return None
    if clock_ms < 5_000:
        return CLOCK_BUCKETS[0]
    return CLOCK_BUCKETS[1] if clock_ms < 15_000 else CLOCK_BUCKETS[2]


def is_bullet_1_0(time_control: str | None) -> bool:
    """True for the PGN TimeControl of a 1+0 game."""
    return time_control == "60+0"


def is_held_out(game_id: str, held_out_fraction: float = 0.3) -> bool:
    """
    Stable split **by game**: every position of a game lands on the same side, so
    thresholds tuned on one set are never scored on positions from the same games.
    """
    digest = hashlib.sha256(game_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") / 2**32 < held_out_fraction


def decider_clock_ms(clocks_ms: list[int | None], ply: int, initial_ms: int | None) -> int | None:
    """
    Clock of the player who must reply to `ply`, at the moment they start thinking.

    `%clk` is the mover's time after their own move, so the replier's clock is their
    annotation two plies earlier — or the initial time when they have not moved yet.
    """
    reply_ply = ply + 1
    previous = reply_ply - 2
    if previous < 0:
        return initial_ms
    return clocks_ms[previous] if previous < len(clocks_ms) else None


def raw_cliff(lines: list[dict]) -> float | None:
    """Baseline 1: EP gap between the best and second-best reply, ignoring findability."""
    eps = [line["ep"] for line in lines if line.get("ep") is not None]
    if len(eps) < 2:
        return None
    return max(0.0, eps[0] - eps[1])


def brier(samples: list[dict], predictor: str) -> float | None:
    """Mean squared error of a probability predictor against the observed 0/1 label."""
    scored = [s for s in samples if s.get(predictor) is not None]
    if not scored:
        return None
    return sum((s[predictor] - s["failed"]) ** 2 for s in scored) / len(scored)


def calibration_table(samples: list[dict], predictor: str, bins: int = 10) -> list[dict]:
    """
    Predicted vs observed failure rate per rating band, clock bucket and probability bin.

    Each sample needs `band`, `clock`, `failed` (0/1) and the predictor's value in [0, 1].
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for sample in samples:
        value = sample.get(predictor)
        if value is None:
            continue
        index = min(bins - 1, int(value * bins))
        groups[(sample["band"], sample["clock"], index)].append(sample)

    rows = []
    for (band, clock, index), members in sorted(groups.items()):
        rows.append(
            {
                "band": band,
                "clock": clock,
                "bin_low": round(index / bins, 2),
                "n": len(members),
                "predicted": round(sum(m[predictor] for m in members) / len(members), 4),
                "observed": round(sum(m["failed"] for m in members) / len(members), 4),
            }
        )
    return rows


def clock_multipliers(samples: list[dict], predictor: str = "p_fail") -> dict[str, float]:
    """
    One multiplier per clock bucket: observed failure rate / mean predicted P_fail.

    Fit on the tuning set only. A bucket with no data, or no predicted failures, gets 1.0.
    """
    multipliers = {}
    for bucket in CLOCK_BUCKETS:
        members = [s for s in samples if s["clock"] == bucket and s.get(predictor) is not None]
        predicted = sum(s[predictor] for s in members)
        observed = sum(s["failed"] for s in members)
        multipliers[bucket] = round(observed / predicted, 4) if predicted > 0 else 1.0
    return multipliers


def apply_multiplier(value: float | None, clock: str, multipliers: dict[str, float]) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, value * multipliers.get(clock, 1.0)))


def summarize_validation(tuning: list[dict], held_out: list[dict]) -> dict:
    """
    Fit the clock multiplier on `tuning`, then score every predictor on `held_out`.

    `beats_baselines` is the M4 go / no-go signal: the adjusted model must have a strictly
    lower Brier score than the raw cliff and the equally adjusted heuristic baseline, on
    games it was not tuned on.
    """
    multipliers = clock_multipliers(tuning)
    # The heuristic baseline gets its own clock multiplier, fit the same way, so the
    # comparison is like for like: otherwise the adjustment alone could "beat" it.
    heuristic_multipliers = clock_multipliers(tuning, "baseline_heuristic")
    scored = [
        {
            **s,
            "p_fail_adjusted": apply_multiplier(s.get("p_fail"), s["clock"], multipliers),
            "baseline_heuristic_adjusted": apply_multiplier(
                s.get("baseline_heuristic"), s["clock"], heuristic_multipliers
            ),
        }
        for s in held_out
    ]
    scores = {
        name: brier(scored, name)
        for name in (
            "p_fail", "p_fail_adjusted", "baseline_cliff", "baseline_heuristic", "baseline_heuristic_adjusted",
        )
    }
    model = scores["p_fail_adjusted"]
    baselines = [scores["baseline_cliff"], scores["baseline_heuristic_adjusted"]]
    beats = model is not None and all(b is not None and model < b for b in baselines)
    return {
        "tuning_samples": len(tuning),
        "held_out_samples": len(held_out),
        "clock_multipliers": multipliers,
        "brier": scores,
        "beats_baselines": beats,
        "calibration": calibration_table(scored, "p_fail_adjusted"),
    }
