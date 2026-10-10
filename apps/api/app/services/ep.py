"""
Expected points (EP) — the unit for all Chaos Lens work (docs/CHAOS_PLAN.md, rule 4).

EP is the side to move's expected score in [0, 1]: win = 1, draw = 0.5, loss = 0.
Centipawns stay in Phase 1 code only; they are not linear near decided positions.
"""

from __future__ import annotations

import math

# Logistic slope mapping centipawns to a win probability. Fallback only — used when the
# engine reports no WDL (and to convert stored Phase 1 evals for the decided-position skip).
CP_TO_EP_SLOPE = 0.00368208


def wdl_to_ep(wins: int, draws: int, losses: int) -> float:
    """EP from Stockfish `UCI_ShowWDL` counts (per-mille, but any consistent scale works)."""
    total = wins + draws + losses
    if total <= 0 or min(wins, draws, losses) < 0:
        raise ValueError(f"Invalid WDL: {wins}/{draws}/{losses}")
    return (wins + 0.5 * draws) / total


def cp_to_ep(cp: float) -> float:
    """Approximate EP from a centipawn score (side to move's perspective)."""
    # Clamp the exponent so extreme mate-substitute scores cannot overflow.
    exponent = max(-50.0, min(50.0, -CP_TO_EP_SLOPE * cp))
    return 1.0 / (1.0 + math.exp(exponent))


def mate_to_ep(mate: int) -> float:
    """EP for a forced mate: positive = side to move mates, zero or negative = it gets mated."""
    return 1.0 if mate > 0 else 0.0


def line_ep(
    wdl: tuple[int, int, int] | list[int] | None,
    cp: float | None,
    mate: int | None,
) -> float | None:
    """Best available EP for one engine line: WDL first, then mate, then centipawns."""
    if wdl is not None:
        return wdl_to_ep(*wdl)
    if mate is not None:
        return mate_to_ep(mate)
    if cp is not None:
        return cp_to_ep(cp)
    return None


def is_decided(ep: float | None, low: float, high: float) -> bool:
    """True when the game is already decided for the mover; an unknown EP is not decided."""
    if ep is None:
        return False
    return ep < low or ep > high
