"""
Swindle lens — the mirror of squeeze: once the user is clearly losing, did the move set the opponent a real problem
(many ways to go wrong) or drift? And did the opponent then fall for it?

Chaos is switched off in decided positions (config.DECIDED_*), because a problem set while losing says something
different: it is fighting spirit, the swindle. This lens scores exactly those moves, with the same P_fail × stake
measure at the opponent's rating, and checks the opponent's actual reply against the safe set.
"""

from __future__ import annotations

from app.lenses import config
from app.lenses.base import LensResult, PlyContext
from app.lenses.chaos import nearest_elo, position_chaos
from app.lenses.squeeze import line_cp, line_points


class SwindleLens:
    name = "swindle"
    version = "3"  # 3: "clearly losing" in EP (review F8); 2: opponent rating on the model's scale (F1)

    def score(self, ctx: PlyContext) -> LensResult | None:
        if ctx.faced is None or ctx.left is None or not ctx.faced.lines:
            return None
        before, ep_before = line_cp(ctx.faced.lines[0]), line_points(ctx.faced.lines[0])
        if before is None or ep_before is None or ep_before > config.SWINDLE_MAX_EP:
            return None  # only moves made while clearly losing
        data = position_chaos(ctx.left)
        if data is None:
            return None
        elo = nearest_elo(ctx.left.probs_by_elo, ctx.opponent_elo)
        problem = data["chaos"][elo]
        if problem < config.CHAOS_THRESHOLD:
            return LensResult(problem, "drifted", {"edge_before": before, "elo": elo, "p_fail": data["p_fail"][elo]})
        # Did the opponent find a safe reply? Unknown when the game ended or the safe set may be incomplete.
        fell = None
        if ctx.reply_uci:
            if ctx.reply_uci in data["safe_set"]:
                fell = False
            elif data["safe_set_complete"]:
                fell = True
        return LensResult(
            problem,
            "sprung" if fell else "set",
            {
                "edge_before": before,
                "elo": elo,
                "p_fail": data["p_fail"][elo],
                "stake": data["stake"][elo],
                "safe_set": data["safe_set"],
                "reply": ctx.reply_uci,
                "fell": fell,
            },
        )
