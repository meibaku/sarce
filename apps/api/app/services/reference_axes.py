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
AXES = ["Sacrifice rate", "Chaos created", "Calm under fire", "Initiative kept"]


def axis_values(traits: dict[str, float | None]) -> dict[str, int | None]:
    """The You axes (0–100) from trait values (services/you.py trait_values)."""

    def pct(value: float | None) -> int | None:
        return None if value is None else round(value * 100)

    initiative = traits.get("Initiative")
    return {
        "Sacrifice rate": pct(traits.get("Sacrifice")),
        "Chaos created": pct(traits.get("Chaos")),
        "Calm under fire": pct(traits.get("Calm")),
        # Mean chaos score sits around 0–0.5, so it is doubled onto the 0–100 axis.
        "Initiative kept": None if initiative is None else min(100, round(initiative * 200)),
    }


@lru_cache(maxsize=1)
def references() -> dict[str, dict]:
    """{player: {"games": n, "axes": {axis: value}, ...}}; empty when nothing is scored yet."""
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
