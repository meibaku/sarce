"""Chaos budget (app/services/budget.py, plan 3.9)."""

from app.lenses.base import PlyContext, PositionData
from app.lenses.chaos import reply_loss
from app.services.budget import chaos_budget


def row(verdict, cost, loss):
    return {"lens": "chaos", "verdict": verdict, "details": {"objective_cost": cost, "reply_ep_loss": loss}}


def test_budget_sums_cost_and_what_came_back():
    rows = [row("real_chaos", 0.0, 0.3), row("cheap_chaos", 0.2, None), row("calculated_risk", 0.07, 0.1), row(None, 0.5, 0.9)]
    assert chaos_budget(rows) == {"spent": 0.27, "back": 0.4, "net": 0.13, "problems": 3, "unknown": 1}
    assert chaos_budget([row(None, 0.1, 0.1)]) is None


def test_reply_loss_reads_the_played_reply_from_the_stored_lines():
    left = PositionData(lines=[{"move_uci": "a", "ep": 0.6}, {"move_uci": "b", "ep": 0.25}], safe_set_complete=True)
    ctx = PlyContext(ply=3, uci="x", left=left, reply_uci="b")
    assert reply_loss(ctx, {"best_reply_ep": 0.6}) == {"reply": "b", "reply_ep_loss": 0.35}
    assert reply_loss(PlyContext(ply=3, uci="x", left=left, reply_uci="z"), {"best_reply_ep": 0.6})["reply_ep_loss"] is None
    assert reply_loss(PlyContext(ply=3, uci="x", left=left), {"best_reply_ep": 0.6}) == {"reply": None, "reply_ep_loss": None}
