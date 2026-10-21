"""
Style lenses — pure functions over stored data (docs/CHAOS_PLAN.md, rule 3).

A lens never calls Stockfish or a human model. Engines write raw data
(`position_evals`, `human_probs`); lenses read it, so adding a lens never needs re-analysis.
"""

from app.lenses.base import Lens, LensResult, PlyContext, PositionData
from app.lenses.registry import all_lenses, register, score_ply

__all__ = [
    "Lens",
    "LensResult",
    "PlyContext",
    "PositionData",
    "all_lenses",
    "register",
    "score_ply",
]
