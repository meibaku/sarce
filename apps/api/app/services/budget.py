"""
Chaos budget (implementation plan 3.9): what setting problems cost you, and what came back.

For every move where you set a problem (a chaos verdict: real, speculative or unsound), "spent" is its objective
cost — expected points below the engine's best — and "back" is what the opponent's actual reply gave up: the
expected points between their best reply and the one they played (`reply_ep_loss`, stored by the chaos lens
since version 3). Replies outside the stored engine lines are unknown and left out of "back", and counted.
Stored lens rows only; no engine. Shown as two numbers, never as a verdict: a negative net is a style, not a fault.
"""

from __future__ import annotations

PROBLEM_VERDICTS = ("real_chaos", "calculated_risk", "cheap_chaos")


def chaos_budget(rows: list[dict]) -> dict | None:
    """{spent, back, net, problems, unknown} over chaos lens rows; None when no problem was set."""
    problems = [r for r in rows if r.get("lens", "chaos") == "chaos" and r.get("verdict") in PROBLEM_VERDICTS]
    if not problems:
        return None
    spent = back = 0.0
    unknown = 0
    for r in problems:
        details = r.get("details") or {}
        spent += float(details.get("objective_cost") or 0)
        loss = details.get("reply_ep_loss")
        if loss is None:
            unknown += 1
        else:
            back += max(0.0, float(loss))
    return {"spent": round(spent, 2), "back": round(back, 2), "net": round(back - spent, 2), "problems": len(problems), "unknown": unknown}
