"""
"Why this move?" — an explanation of one of your moves from what Sarce actually computed.

For a move it returns:
- `badge`: why it got its badge (!!, ✓, !?, ?!, ?) or none, in the style copy (never Phase 1 labels);
- `brilliant`: each Brilliant rule (brilliant.py, ADR 0004) as a check with the real numbers, so "why isn't
  this Brilliant?" has a concrete answer — the same thresholds the classifier used;
- `chaos`: who falls for the problem it set or faced (P_fail by rating) and the safe replies;
- `lines`: playable examples for the board — what you played and the reply, the engine's top lines, and,
  when there was one, a sacrifice that would have counted as Brilliant.

The engine is a mirror: the numbers come from stored analysis; only the continuations are searched live
(shared engine, a fraction of a second), and if the engine isn't available the stored first moves are used.
"""

from __future__ import annotations

import io

import chess
import chess.pgn

from app.config import settings
from app.db.supabase import get_supabase
from app.services.brilliant import FIND_RATE_MAX, MAX_BRILLIANT_EVAL_LOSS, MIN_BRILLIANT_SACRIFICE_VALUE
from app.services.library import real_offer
from app.services.position_evals import fen_key
from app.services.review import LADDER, ladder_p_fail, nearest_rung
from app.services.summary import move_label

LINE_NODES = 400_000


def pawns(cp: int | None, mate: int | None) -> float | None:
    if mate is not None:
        return 100.0 if mate > 0 else -100.0
    return None if cp is None else round(cp / 100, 2)


def fmt(p: float | None) -> str:
    if p is None:
        return "?"
    if abs(p) >= 99:
        return "mate" if p > 0 else "getting mated"
    return f"{p:+.1f}"


def steps(board: chess.Board, ucis: list[str]) -> list[dict]:
    """A line as board steps: [{san, uci, fen}] from `board` (left unchanged)."""
    b, out = board.copy(), []
    for uci in ucis:
        move = chess.Move.from_uci(uci)
        if move not in b.legal_moves:
            break
        out.append({"san": b.san(move), "uci": uci, "fen": b.fen()})
        b.push(move)
        out[-1]["fen"] = b.fen()
    return out


def brilliant_checks(board: chess.Board, move: chess.Move, eval_before: float | None, eval_after: float | None, find_prob: float | None, rung: int) -> list[dict]:
    """Each Brilliant rule, with whether it held and the number behind it."""
    # The strict test (ADR 0007): the number the Brilliant verdict actually uses.
    offered = real_offer(board, move)
    allowed = min(settings.brilliant_eval_margin, MAX_BRILLIANT_EVAL_LOSS)
    gap = None if eval_before is None or eval_after is None else round(max(0.0, eval_before - eval_after), 2)
    legal = board.legal_moves.count()
    return [
        {
            "rule": "A real sacrifice",
            "passed": offered >= MIN_BRILLIANT_SACRIFICE_VALUE,
            "detail": f"You offered {offered} point{'s' if offered != 1 else ''} of material; Brilliant needs at least {MIN_BRILLIANT_SACRIFICE_VALUE} (a minor piece). Pawns alone don't count."
            if offered
            else f"Nothing was really on offer (a piece counts when something cheaper attacks it, or it is undefended); Brilliant needs at least {MIN_BRILLIANT_SACRIFICE_VALUE} points.",
        },
        {
            "rule": "It holds up",
            "passed": gap is not None and gap <= allowed,
            "detail": f"After it the engine rates the position {gap:.2f} pawns below its first choice; Brilliant allows {allowed:.2f}."
            if gap is not None
            else "There was no engine evaluation to judge it by.",
        },
        {
            "rule": "Not already decided",
            "passed": eval_before is not None and eval_before <= settings.brilliant_winning_margin,
            "detail": f"You were {fmt(eval_before)} before the move; a sacrifice only counts when you weren't already above +{settings.brilliant_winning_margin:.0f}."
            if eval_before is not None
            else "There was no engine evaluation to judge it by.",
        },
        {
            "rule": "A real choice",
            "passed": legal > 1,
            "detail": f"You had {legal} legal moves." if legal > 1 else "It was the only legal move, so there was nothing to find.",
        },
        {
            "rule": "Hard to find",
            "passed": find_prob is not None and find_prob <= FIND_RATE_MAX,
            "detail": f"About {round(find_prob * 100)}% of {rung}-rated players would play it; Brilliant needs {round(FIND_RATE_MAX * 100)}% or fewer."
            if find_prob is not None
            else "No human-model estimate for this position yet (it fills in with the Chaos Lens pass).",
        },
    ]


def badge_reason(glyph: str | None, chaos: dict, survival: dict, is_brilliant: bool, cost: float | None) -> str:
    """Why the move got its badge, in the style copy."""
    if is_brilliant or glyph == "!!":
        return "Brilliant: a sound sacrifice that players at this level rarely find."
    sv, cv = survival.get("verdict"), chaos.get("verdict")
    if sv == "missed":
        return "Didn't hold: your opponent set a problem here and this reply let it through."
    if cv == "cheap_chaos":
        return "Unsound chaos: you set a problem, but it cost more than it asked of your opponent" + (f" (about {cost:.1f} pawns)." if cost else ".")
    if cv == "real_chaos":
        return "A real problem: your move stayed sound and left your opponent few safe replies."
    if sv == "survived":
        return "Safe reply found: your opponent set a problem and you found a way through."
    if cv == "calculated_risk":
        return "Speculative: a sharp try the engine doesn't fully trust, but it held."
    if glyph == "?!":
        return "Check-in: your pace changed around this move; only you know why."
    return "No badge: a normal move that didn't set or face a real problem."


class ExplainService:
    def __init__(self, lines_engine=None) -> None:
        # `lines_engine.pv_lines(board, multipv)`; the shared bot engine in the app, a fake in tests.
        self.lines_engine = lines_engine

    def why(self, game_id: str, ply: int) -> dict | None:
        sb = get_supabase()
        games = sb.table("games").select("pgn, user_color, opponent_rating").eq("id", game_id).limit(1).execute().data or []
        if not games:
            return None
        game = games[0]
        rows = sb.table("game_moves").select("ply, san, uci, quality, cp_loss, eval_before, eval_after, is_brilliant, signals, best_uci, best_san, pv").eq("game_id", game_id).eq("ply", ply).limit(1).execute().data or []
        if not rows:
            return None  # not one of your moves, or not analysed yet
        row = rows[0]
        pgn = chess.pgn.read_game(io.StringIO(game.get("pgn") or ""))
        board = pgn.board() if pgn else chess.Board()
        mainline = list(pgn.mainline_moves()) if pgn else []
        for m in mainline[:ply]:
            board.push(m)
        move = chess.Move.from_uci(row["uci"])
        lens = {r["lens"]: r for r in sb.table("move_lens_scores").select("lens, score, verdict, details").eq("game_id", game_id).eq("ply", ply).execute().data or []}
        chaos, survival = lens.get("chaos") or {}, lens.get("survival") or {}

        rung = nearest_rung(game.get("opponent_rating"))
        probs_rows = sb.table("human_probs").select("probs").eq("fen_key", fen_key(board)).eq("elo", rung).limit(1).execute().data or []
        find_prob = (probs_rows[0]["probs"] or {}).get(row["uci"], 0.0) if probs_rows else None

        cost = ((lens.get("soundness") or {}).get("details") or {}).get("objective_cost")
        glyph = "!!" if row.get("is_brilliant") else None
        checks = brilliant_checks(board, move, row.get("eval_before"), row.get("eval_after"), find_prob, rung)

        # A problem you faced (survival) speaks about you; one you set (chaos) about your opponent.
        source = survival if survival.get("verdict") in ("survived", "missed") else chaos
        details = source.get("details") or {}
        p_fail = ladder_p_fail(details)
        safe = list(details.get("safe_set") or [])[:5]
        # Safe replies are moves in the position the problem was set in: after your move for chaos,
        # before it for survival (the problem your opponent set you).
        where = board.copy()
        if source is chaos:
            where.push(move)
        safe_san = []
        for uci in safe:
            try:
                safe_san.append(where.san(chess.Move.from_uci(uci)))
            except ValueError:
                continue

        return {
            "gameId": game_id,
            "ply": ply,
            "label": move_label(ply, row.get("san")),
            "fenBefore": board.fen(),
            "orientation": game.get("user_color") or "white",
            "badge": badge_reason(glyph, chaos, survival, bool(row.get("is_brilliant")), None if cost is None else float(cost)),
            "isBrilliant": bool(row.get("is_brilliant")),
            "brilliant": checks,
            "evalBefore": row.get("eval_before"),
            "evalAfter": row.get("eval_after"),
            "best": row.get("best_san"),
            "chaos": {
                "verdict": source.get("verdict"),
                "faced": source is survival,
                "pFail": p_fail,
                "rungs": LADDER,
                "safeReplies": safe_san,
            },
            "lines": self._lines(board, move, row),
        }

    def _lines(self, board: chess.Board, move: chess.Move, row: dict) -> list[dict]:
        """Playable examples: your move and the reply, the engine's top lines, a sacrifice that would count."""
        lines: list[dict] = []
        try:
            if self.lines_engine is None:
                raise RuntimeError("no engine")
            top = self.lines_engine.pv_lines(board, multipv=3)
            after = board.copy()
            after.push(move)
            reply = self.lines_engine.pv_lines(after, multipv=1) if not after.is_game_over() else []
        except Exception:
            # Engine unavailable: the stored candidates (first moves only) still show the alternatives.
            top = [{"uci": [c["uci"]], "cp": None if c.get("eval") is None else round(c["eval"] * 100), "mate": None} for c in (row.get("pv") or []) if c.get("uci")]
            reply = []
        played = {
            "title": "What you played",
            "note": "Your move, then the engine's best reply.",
            "eval": fmt(None if not reply else (-pawns(reply[0]["cp"], reply[0]["mate"]) if pawns(reply[0]["cp"], reply[0]["mate"]) is not None else None)),
            "steps": steps(board, [move.uci()] + (reply[0]["uci"] if reply else [])),
            "kind": "played",
        }
        lines.append(played)
        best_eval = pawns(top[0]["cp"], top[0]["mate"]) if top else None
        for i, line in enumerate(top):
            first = line["uci"][0]
            same = first == move.uci()
            lines.append({
                "title": "The engine's first choice" if i == 0 else f"Alternative {i}",
                "note": "This is the move you played." if same else ("The line the engine prefers." if i == 0 else "Also playable."),
                "eval": fmt(pawns(line["cp"], line["mate"])),
                "steps": steps(board, line["uci"]),
                "kind": "engine",
            })
        # A sacrifice among the engine's lines that would have passed the material and soundness rules.
        if not row.get("is_brilliant") and best_eval is not None:
            for line in top:
                cand = chess.Move.from_uci(line["uci"][0])
                ev = pawns(line["cp"], line["mate"])
                # The stricter test (attacked by something cheaper, or undefended), so the example is a
                # sacrifice a person would recognise, not just a piece a reply could land on.
                if cand != move and real_offer(board, cand) >= MIN_BRILLIANT_SACRIFICE_VALUE and ev is not None and best_eval - ev <= MAX_BRILLIANT_EVAL_LOSS:
                    lines.append({
                        "title": "A sacrifice that would count",
                        "note": "Gives up material and the engine still rates it among the best: the shape of a Brilliant move here.",
                        "eval": fmt(ev),
                        "steps": steps(board, line["uci"]),
                        "kind": "brilliant",
                    })
                    break
        return [ln for ln in lines if ln["steps"]]
