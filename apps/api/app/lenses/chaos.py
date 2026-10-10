"""
Chaos lens — how much practical trouble a move creates for a human opponent.

Chaos(Elo) = P_fail(Elo) x Stake, from docs/CHAOS_PLAN.md "Core formulas".
"""

from __future__ import annotations

from app.lenses import config
from app.lenses.base import LensResult, PlyContext, PositionData


def split_safe(lines: list[dict], safe_tol: float) -> tuple[list[dict], list[dict]]:
    """Split stored reply lines into (safe, non-safe) by EP distance from the best reply."""
    scored = [line for line in lines if line.get("ep") is not None]
    if not scored:
        return [], []
    best = scored[0]["ep"]
    safe = [line for line in scored if best - line["ep"] <= safe_tol]
    return safe, [line for line in scored if best - line["ep"] > safe_tol]


def nearest_elo(probs_by_elo: dict[int, dict], target: int | None) -> int | None:
    """The stored Elo closest to `target` (or to the default when the rating is unknown)."""
    if not probs_by_elo:
        return None
    wanted = target or config.DEFAULT_ELO
    return min(probs_by_elo, key=lambda elo: (abs(elo - wanted), elo))


def position_chaos(position: PositionData, safe_tol: float = config.SAFE_TOL) -> dict | None:
    """
    P_fail per Elo, Stake and Chaos per Elo for the side to move in `position`.

    Stake is weighted over the non-safe replies that have a stored EP, with probabilities
    renormalized over that subset; `unstored_mass` reports the failure probability that
    had no stored EP. Returns None when there is nothing to compute from.
    """
    safe, non_safe = split_safe(position.lines, safe_tol)
    if not safe or not position.probs_by_elo:
        return None
    best_ep = safe[0]["ep"]
    safe_moves = {line["move_uci"] for line in safe}

    p_fail, stake, chaos, unstored = {}, {}, {}, {}
    for elo, probs in position.probs_by_elo.items():
        fail = max(0.0, 1.0 - sum(probs.get(uci, 0.0) for uci in safe_moves))
        weights = [(probs.get(line["move_uci"], 0.0), line["ep"]) for line in non_safe]
        stored_mass = sum(w for w, _ in weights)
        if stored_mass > 0:
            lost_ep = sum(w * ep for w, ep in weights) / stored_mass
        elif non_safe:
            # The model gives the stored non-safe replies no weight: use them evenly.
            lost_ep = sum(ep for _, ep in weights) / len(weights)
        else:
            lost_ep = best_ep  # every stored reply is safe: nothing measurable at stake
        p_fail[elo] = round(fail, 4)
        stake[elo] = round(max(0.0, best_ep - lost_ep), 4)
        chaos[elo] = round(p_fail[elo] * stake[elo], 4)
        unstored[elo] = round(max(0.0, fail - stored_mass), 4)

    return {
        "p_fail": p_fail,
        "stake": stake,
        "chaos": chaos,
        "unstored_mass": unstored,
        "safe_set": sorted(safe_moves),
        "safe_set_complete": position.safe_set_complete,
        "best_reply_ep": best_ep,
    }


def is_decided(ep_before: float | None) -> bool:
    return ep_before is not None and not (config.DECIDED_LOW <= ep_before <= config.DECIDED_HIGH)


class ChaosLens:
    """Scores the trouble the user's move created for the opponent."""

    name = "chaos"
    version = "1"

    def score(self, ctx: PlyContext) -> LensResult | None:
        if ctx.left is None:
            return None
        if is_decided(ctx.ep_before):
            return LensResult(0.0, None, {"decided": True})
        data = position_chaos(ctx.left)
        if data is None:
            return None

        elo = nearest_elo(ctx.left.probs_by_elo, ctx.opponent_elo)
        chaos = data["chaos"][elo]
        cost = ctx.objective_cost
        verdict = None
        if chaos >= config.CHAOS_THRESHOLD and cost is not None:
            if cost <= config.REAL_CHAOS_MAX_COST:
                verdict = "real_chaos"
            elif cost > config.CHEAP_CHAOS_MIN_COST:
                verdict = "cheap_chaos"
            else:
                verdict = "calculated_risk"
        return LensResult(chaos, verdict, {**data, "elo": elo, "objective_cost": cost})
