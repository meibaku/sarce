"""
Survival lens — the mirror of chaos: when the opponent set a high-chaos problem,
did the user find a safe reply?
"""

from __future__ import annotations

from app.lenses import config
from app.lenses.base import LensResult, PlyContext
from app.lenses.chaos import is_decided, nearest_elo, position_chaos


class SurvivalLens:
    name = "survival"
    version = "2"  # 2: opponent rating on the human model's scale (review F1)

    def score(self, ctx: PlyContext) -> LensResult | None:
        if ctx.faced is None or is_decided(ctx.ep_before):
            return None
        data = position_chaos(ctx.faced)
        if data is None:
            return None
        # The user's own rating is not stored; the opponent's is the closest proxy in a paired game.
        elo = nearest_elo(ctx.faced.probs_by_elo, ctx.opponent_elo)
        faced_chaos = data["chaos"][elo]
        if faced_chaos < config.CHAOS_THRESHOLD:
            return None  # no real problem was set, so there is nothing to survive

        survived = ctx.uci in data["safe_set"]
        return LensResult(
            1.0 if survived else 0.0,
            "survived" if survived else "missed",
            {**data, "elo": elo, "faced_chaos": faced_chaos},
        )
