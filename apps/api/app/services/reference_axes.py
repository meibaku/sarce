"""
Reference players on the You axes, in the same chaos terms as you (docs/DESIGN.md, screen 5).

`data/reference_axes.json` is written by `scripts/process_tal_chaos.py`, which runs a sample of a
reference player's games through the same Phase 1 classification and Chaos Lens as yours, entirely
in memory, and stores only the four axis values. No file, or no entry for a player, means the You
screen says that player isn't scored yet instead of drawing an invented dot.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "data" / "reference_axes.json"
AXES = ["Sacrifices per 1,000 moves", "Chaos created", "Calm under fire", "Initiative kept"]


def axis_values(traits: dict[str, float | None]) -> dict[str, int | None]:
    """The You axes (0–100) from trait values (services/you.py trait_values)."""

    def pct(value: float | None) -> int | None:
        return None if value is None else round(value * 100)

    initiative = traits.get("Initiative")
    sacrifice = traits.get("Sacrifice")
    return {
        # Real sacrifices are rare (Tal: about 5 in 1,000 moves), so this axis counts them per 1,000 moves, capped at
        # 100: as a percentage every player would round to 0-2 (review F2).
        "Sacrifices per 1,000 moves": None if sacrifice is None else min(100, round(sacrifice * 1000)),
        "Chaos created": pct(traits.get("Chaos")),
        "Calm under fire": pct(traits.get("Calm")),
        # Mean chaos score sits around 0–0.5, so it is doubled onto the 0–100 axis.
        "Initiative kept": None if initiative is None else min(100, round(initiative * 200)),
    }


POSITIONS_PATH = PATH.with_name("reference_positions.json")


@lru_cache(maxsize=1)
def reference_positions() -> dict[str, list[dict]]:
    """{player: [{fen, san, uci, eco, year, opponent, event}]} from scripts/build_reference_positions.py."""
    try:
        return json.loads(POSITIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def in_your_openings(positions: list[dict], ecos: list[str], seed: int, count: int = 3) -> list[dict]:
    """
    Up to `count` reference positions from your openings: exact ECO codes first (most played first),
    then the same ECO family (C4x), rotated by `seed` so the queue changes from day to day.
    """
    chosen: list[dict] = []
    for match in (lambda p, e: p["eco"] == e, lambda p, e: p["eco"][:2] == e[:2]):
        for eco in ecos:
            pool = [p for p in positions if match(p, eco) and p not in chosen]
            if pool:
                chosen.append(pool[seed % len(pool)])
            if len(chosen) >= count:
                return chosen
    return chosen


@lru_cache(maxsize=1)
def references() -> dict[str, dict]:
    """{player: {"games": n, "axes": {axis: value}, ...}}; empty when nothing is scored yet."""
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
