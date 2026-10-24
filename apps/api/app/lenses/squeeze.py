"""
Squeeze lens — the calm counterpart to chaos: once the user is clearly winning, did the move keep the advantage
and leave the opponent little room (few replies that hold), or did it give them air?

Chaos asks "did you set a problem they will miss?"; squeeze asks "did you take their options away?" — the
Petrosian/Karpov way of converting an advantage. The edge and its cost are expected points (review F8); the
opponent's room is counted in centipawns, because on the losing side EP compresses and would hide which replies
still hold.
"""

from __future__ import annotations

from app.lenses import config
from app.lenses.base import LensResult, PlyContext
from app.services.ep import cp_to_ep

MATE_CP = 10_000  # a forced mate scores beyond any material edge


def line_cp(line: dict) -> float | None:
    """A line's score in centipawns from its side to move; mates map past any material score."""
    if line.get("mate") is not None:
        mate = int(line["mate"])
        return MATE_CP - abs(mate) if mate > 0 else -MATE_CP + abs(mate)
    return None if line.get("cp") is None else float(line["cp"])


def line_points(line: dict) -> float | None:
    """A line's expected points for its side to move: the stored EP, else converted from its score."""
    if line.get("ep") is not None:
        return float(line["ep"])
    cp = line_cp(line)
    return None if cp is None else cp_to_ep(cp)


def room(lines: list[dict], complete: bool) -> tuple[int, bool]:
    """Opponent replies within SQUEEZE_REPLY_CP of their best, and whether that count is exact."""
    scores = [s for s in (line_cp(ln) for ln in lines) if s is not None]
    if not scores:
        return 0, False
    best = scores[0]
    n = sum(1 for s in scores if s >= best - config.SQUEEZE_REPLY_CP)
    # Every stored line holds and the search may have stopped short: the true count could be higher.
    return n, complete or n < len(scores)


class SqueezeLens:
    name = "squeeze"
    version = "2"  # 2: edge and cost in EP (review F8)

    def score(self, ctx: PlyContext) -> LensResult | None:
        if ctx.faced is None or ctx.left is None or not ctx.faced.lines or not ctx.left.lines:
            return None
        before, reply = line_cp(ctx.faced.lines[0]), line_cp(ctx.left.lines[0])
        ep_before, ep_reply = line_points(ctx.faced.lines[0]), line_points(ctx.left.lines[0])
        if before is None or reply is None or ep_before is None or ep_reply is None or ep_before < config.SQUEEZE_MIN_EP:
            return None  # only moves made while clearly winning
        after = -reply  # the user's edge after the move, from the opponent's best reply
        cost = max(0.0, before - after)
        cost_ep = max(0.0, ep_before - (1 - ep_reply))
        n, exact = room(ctx.left.lines, ctx.left.safe_set_complete)

        if cost_ep > config.SQUEEZE_AIR_EP:
            verdict, score = "gave_air", 0.0
        elif n <= config.SQUEEZE_TIGHT_REPLIES and cost_ep <= config.SQUEEZE_KEEP_EP:
            verdict, score = "squeezed", 1.0
        else:
            verdict = "kept"
            # More holding replies left for the opponent, the looser the grip.
            score = round(max(0.0, 1 - (n - config.SQUEEZE_TIGHT_REPLIES) / config.SQUEEZE_ROOM_SPAN), 3)
        return LensResult(
            score,
            verdict,
            {"edge_before": before, "edge_after": after, "cost_cp": cost, "cost_ep": round(cost_ep, 3), "replies_that_hold": n, "replies_exact": exact},
        )
