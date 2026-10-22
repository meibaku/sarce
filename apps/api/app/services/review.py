"""
Review (docs/DESIGN.md, screen 4): every moment of a game with its board, the squares that
mattered, the question to ask, "who falls for this" (P_fail across the rating ladder), the
engine's mirror line and the player's intent note.

The engine view is only sent to the client; the UI keeps it hidden until the player has noted
their intent or asked for it. Copy never grades: "didn't hold", never failure words.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.db.supabase import get_supabase
from app.services.distraction import flagged_plies
from app.services.home import format_time_control, is_calibrated, pick_moments
from app.services.pgn_parser import mainline_positions
from app.services.summary import clock_label, move_label

LADDER = [800, 1200, 1600, 2000, 2400]
MAX_REVIEW_MOMENTS = 8
INTENTS = ("calculated", "intuitive", "bluff")
SOUND_COST = 0.05


def ladder_p_fail(details: dict | None) -> list[float] | None:
    """P_fail at 800…2400 from a chaos or survival lens row, or None without human-model data."""
    p_fail = (details or {}).get("p_fail") or {}
    values = [p_fail.get(str(elo)) for elo in LADDER]
    return None if any(v is None for v in values) else [round(float(v), 4) for v in values]


def nearest_rung(elo: int | None) -> int:
    if not elo:
        return 1600
    return min(LADDER, key=lambda rung: abs(rung - elo))


def falls_line(kind: str, p_fail: list[float] | None, opponent_elo: int | None, calibrated: bool) -> str:
    """One sentence under the chart. Rounded to tenths of players: the model is calibrated, not exact."""
    if p_fail is None:
        return "No human-model data for this move."
    rung = nearest_rung(opponent_elo)
    p = p_fail[LADDER.index(rung)]
    caveat = "" if calibrated else " (uncalibrated outside one-minute games)"
    if kind == "survived":
        return f"About {round(p * 100)}% of players at {rung} fall for this here. You found the safe reply{caveat}."
    if kind == "missed":
        return f"About {round(p * 100)}% of players at {rung} fall for this here{caveat}."
    return f"At {rung}, about {round(p * 10)} in 10 players miss the safe reply here{caveat}."


def ask_for(glyph: str, kind: str, sacrifice: bool) -> str:
    if glyph == "!!" and sacrifice:
        return "You gave up material. What were you going for?"
    if kind == "survived":
        return "Did you see the trap, or was it instinct?"
    if kind == "missed":
        return "What did you expect here?"
    if glyph == "!?":
        return "Calculated, intuitive or a bluff?"
    if glyph == "?":
        return "What were you going for here?"
    if glyph == "?!":
        return "Was something going on at this move?"
    return "Did you mean to set this problem?"


def mirror_line(objective_cost: float | None, best_san: str | None, played_san: str | None) -> str:
    """The engine as a mirror: what it measured, never a verdict on the player."""
    if objective_cost is None:
        return "The engine has no measurement for this move."
    if objective_cost <= SOUND_COST:
        return f"Sound: the position stayed within {objective_cost:.2f} expected points of best."
    if best_san and best_san != played_san:
        return f"The engine preferred {best_san}, {objective_cost:.2f} expected points better."
    return f"The engine measured a cost of {objective_cost:.2f} expected points."


def _square(uci: str | None, part: str) -> str | None:
    if not uci or len(uci) < 4:
        return None
    return uci[:2] if part == "from" else uci[2:4]


def hot_squares(kind: str, move_uci: str | None, safe_set: list[str], previous_uci: str | None) -> list[str]:
    """Squares that mattered: the move itself, plus the defence for a problem set, or the trap faced."""
    squares = [_square(move_uci, "to"), _square(move_uci, "from")]
    if kind in ("survived", "missed"):
        squares.insert(1, _square(previous_uci, "to"))
    elif safe_set:
        squares.insert(1, _square(safe_set[0], "to"))
    seen: list[str] = []
    for sq in squares:
        if sq and sq not in seen:
            seen.append(sq)
    return seen[:3]


def plan_outcome(ply: int, ideas: list[dict]) -> str | None:
    """What became of the idea window around this move, from the intention tagger."""
    for idea in ideas:
        if idea["start_ply"] <= ply <= idea["end_ply"]:
            end = idea["end_ply"] // 2 + 1
            if idea["verdict"] == "worked":
                return f"Your plan happened: the idea landed by move {end}."
            if idea["verdict"] == "refuted":
                return f"The idea was met by move {end}."
    return None


class ReviewService:
    def review(self, game_id: str) -> dict | None:
        sb = get_supabase()
        rows = (
            sb.table("games")
            .select("id, pgn, opponent, opponent_rating, result, time_control, user_color, clocks_ms")
            .eq("id", game_id)
            .limit(1)
            .execute()
            .data
        )
        if not rows:
            return None
        game = rows[0]
        initial_fen, line = mainline_positions(game.get("pgn") or "")
        moves = sb.table("game_moves").select("ply, san, uci, quality, is_brilliant, signals, best_san").eq("game_id", game_id).order("ply").execute().data or []
        lens_rows = sb.table("move_lens_scores").select("ply, lens, score, verdict, details").eq("game_id", game_id).execute().data or []
        ideas = sb.table("game_ideas").select("family, start_ply, end_ply, verdict, is_pivot").eq("game_id", game_id).order("start_ply").execute().data or []
        notes = {n["ply"]: n for n in (sb.table("move_annotations").select("ply, intent_type, note").eq("game_id", game_id).execute().data or [])}

        lens_by_ply: dict[int, dict] = {}
        for row in lens_rows:
            lens_by_ply.setdefault(row["ply"], {})[row["lens"]] = row
        by_ply = {m["ply"]: m for m in moves}
        clocks = game.get("clocks_ms") or []
        calibrated = is_calibrated(game.get("time_control"))
        opponent_elo = game.get("opponent_rating")

        moments = []
        for m in pick_moments(moves, lens_by_ply, limit=MAX_REVIEW_MOMENTS, checkin=flagged_plies(game, moves, lens_rows)):
            ply = m["ply"]
            lenses = lens_by_ply.get(ply, {})
            survival = lenses.get("survival") or {}
            chaos = lenses.get("chaos") or {}
            kind = survival.get("verdict") if survival.get("verdict") in ("survived", "missed") else "set"
            source = survival if kind != "set" else chaos
            details = source.get("details") or {}
            p_fail = ladder_p_fail(details)
            move = by_ply.get(ply, {})
            note = notes.get(ply)
            cost = ((lenses.get("soundness") or {}).get("details") or {}).get("objective_cost")
            moments.append({
                **m,
                "label": move_label(ply, m.get("san")),
                "clock": clock_label(clocks[ply] if ply < len(clocks) else None),
                "kind": kind,
                "ask": ask_for(m["glyph"], kind, "sacrifice" in (move.get("signals") or [])),
                "hot": hot_squares(kind, move.get("uci"), details.get("safe_set") or [], line[ply - 1]["uci"] if 0 < ply <= len(line) else None),
                "pFail": p_fail,
                "fallsLine": falls_line(kind, p_fail, opponent_elo, calibrated),
                "mirror": mirror_line(None if cost is None else float(cost), move.get("best_san"), m.get("san")),
                "plan": plan_outcome(ply, ideas),
                "intent": {"type": note["intent_type"], "note": note["note"]} if note else None,
            })

        # Closing it out (squeeze lens): moves made while clearly winning that tightened the grip or gave air back.
        closing = []
        for ply in sorted(lens_by_ply):
            sq = lens_by_ply[ply].get("squeeze")
            if not sq or sq.get("verdict") not in ("squeezed", "gave_air"):
                continue
            d = sq.get("details") or {}
            closing.append({
                "ply": ply,
                "label": move_label(ply, by_ply.get(ply, {}).get("san")),
                "verdict": sq["verdict"],
                "edgeBefore": round(float(d.get("edge_before") or 0) / 100, 1),
                "edgeAfter": round(float(d.get("edge_after") or 0) / 100, 1),
                "holding": d.get("replies_that_hold"),
                "best": by_ply.get(ply, {}).get("best_san") if sq["verdict"] == "gave_air" else None,
            })

        # Fighting back (swindle lens): problems set while clearly losing, and whether the opponent fell for them.
        fighting = []
        for ply in sorted(lens_by_ply):
            sw = lens_by_ply[ply].get("swindle")
            if not sw or sw.get("verdict") not in ("set", "sprung"):
                continue
            d = sw.get("details") or {}
            fighting.append({
                "ply": ply,
                "label": move_label(ply, by_ply.get(ply, {}).get("san")),
                "verdict": sw["verdict"],
                "edgeBefore": round(float(d.get("edge_before") or 0) / 100, 1),
                "pFail": d.get("p_fail"),
            })

        return {
            "gameId": game_id,
            "opponent": game.get("opponent"),
            "result": game.get("result"),
            "userColor": game.get("user_color"),
            "timeControl": format_time_control(game.get("time_control")),
            "calibrated": calibrated,
            "initialFen": initial_fen,
            "positions": [{"ply": p["ply"], "san": p["san"], "uci": p["uci"], "fen": p["fen"]} for p in line],
            "moments": moments,
            "closingOut": closing,
            "fightingBack": fighting,
            "ideas": [
                {"family": i["family"], "startPly": i["start_ply"], "endPly": i["end_ply"], "verdict": i["verdict"], "isPivot": i["is_pivot"]}
                for i in ideas
            ],
        }

    def save_intent(self, game_id: str, ply: int, intent_type: str | None, note: str, user_id: str | None) -> dict:
        if intent_type is not None and intent_type not in INTENTS:
            raise ValueError(f"intent type must be one of {INTENTS}")
        row = {
            "game_id": game_id,
            "ply": ply,
            "intent_type": intent_type,
            "note": note.strip()[:2000],
            "user_id": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        get_supabase().table("move_annotations").upsert(row, on_conflict="game_id,ply").execute()
        return {"type": intent_type, "note": row["note"]}
