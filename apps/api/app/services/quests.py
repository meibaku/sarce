"""
Weekly quests (implementation plan 3.6): the week's focus (3.2) as something to do.

A quest is the focus trait and its target, three drills from your own games where that trait's lens fired (a
squeeze you let go for Grip, a threat you let through for Foresight, …), and a reference player whose value on
that trait is above yours: "Play like Tal this week". Only four traits have reference values today (Sacrifice,
Chaos, Calm, Initiative, from `reference_axes`); the other five have no reference player until the references are
rescored on every trait (plan 2.1), and the quest rests on your own range alone. Reference values are provisional
for the same reason, and say so.

Drills go to the front of Train (source "quest"). The Recap reads the verdict from 3.2 ("done", "held", "next
week") and how many quest drills you answered: never "failed".
"""

from __future__ import annotations

import io

import chess
import chess.pgn

from app.db.supabase import get_supabase
from app.services.reference_axes import axis_values, references
from app.services.summary import move_label

TRAIT_AXIS = {
    "Sacrifice": "Sacrifices per 1,000 moves",
    "Chaos": "Chaos created",
    "Calm": "Calm under fire",
    "Initiative": "Initiative kept",
}
# Where each trait's drills come from: (lens, verdicts that mark a chance to practise, title, detail).
LENS_DRILLS = {
    "Grip": ("squeeze", ("gave_air",), "Keep it tight", "You were winning and gave counterplay back here. Find the move that keeps the grip."),
    "Fight": ("swindle", ("drifted",), "Set them a problem", "You were losing and let the game drift. Find the move that asks them a question."),
    "Clock": ("clock", ("rushed",), "Take the second here", "One move was clearly best and it went fast. Find it with time to think."),
    "Foresight": ("prophylaxis", ("let_through",), "Stop their idea", "Their threat came through after this. Find the move that takes it away."),
    "Defence": ("survival", ("missed",), "Find the safe reply", "A problem was set for you here. Find the reply that holds."),
    "Chaos": ("chaos", ("cheap_chaos",), "Ask a sound question", "You set a problem here, but it cost too much. Find the move that keeps it sound."),
    "Initiative": ("chaos", ("cheap_chaos",), "Keep the pressure, soundly", "Find the move that keeps the pressure without giving ground."),
}
QUEST_DRILLS = 3
GAMES_READ = 60
VERDICT = {"up": "done", "held": "held", "down": "next week"}


def reference_for(trait: str, value: float) -> dict | None:
    """The reference player furthest above you on this trait's axis, or None (no axis, or no one above you)."""
    axis = TRAIT_AXIS.get(trait)
    if axis is None:
        return None
    yours = axis_values({trait: value}).get(axis)
    if yours is None:
        return None
    above = [(player, ref["axes"].get(axis)) for player, ref in references().items() if ref["axes"].get(axis) is not None]
    above = [(p, v) for p, v in above if v > yours]
    if not above:
        return None
    player, theirs = max(above, key=lambda pv: pv[1])
    return {"player": player, "label": f"{player} (provisional)", "axis": axis, "theirs": theirs, "yours": yours}


def quest_drills(user_id: str | None, trait: str, limit: int = QUEST_DRILLS) -> list[dict]:
    """Up to `limit` positions from your recent games where this trait's lens marked a chance to practise."""
    sb = get_supabase()
    q = sb.table("games").select("id, opponent, pgn").eq("analysis_status", "complete").neq("source", "sarce_bot").order("played_at", desc=True).limit(GAMES_READ)
    if user_id:
        q = q.eq("user_id", user_id)
    games = {g["id"]: g for g in (q.execute().data or [])}
    if not games:
        return []
    if trait == "Sacrifice":
        chances = [(r["game_id"], r["ply"]) for r in moves_with_signal(list(games), "near_brilliant:")]
        title, detail = "Your almost-Brilliant move", "Your sacrifice here missed one Brilliant condition. Find the engine's choice, then compare it with yours."
    elif trait in LENS_DRILLS:
        lens, verdicts, title, detail = LENS_DRILLS[trait]
        rows = paged(
            lambda ids: sb.table("move_lens_scores").select("game_id, ply").in_("game_id", ids).eq("lens", lens).in_("verdict", list(verdicts)).order("game_move_id"),
            list(games),
        )
        chances = [(r["game_id"], r["ply"]) for r in rows]
    else:  # Calm: moves where the evaluation swung
        chances = [(r["game_id"], r["ply"]) for r in moves_with_signal(list(games), "evaluation_swing")]
        title, detail = "Keep it level", "The game swung after this move. Find the one that keeps it steady."
    if not chances:
        return []
    best = {
        (m["game_id"], m["ply"]): m
        for m in paged(lambda ids: sb.table("game_moves").select("game_id, ply, san, best_san").in_("game_id", ids).order("id"), list({g for g, _ in chances}))
    }
    items, seen_games = [], set()
    for game_id, ply in chances:
        move = best.get((game_id, ply))
        if not move or not move.get("best_san") or move.get("best_san") == move.get("san") or game_id in seen_games:
            continue
        board = board_before(games[game_id].get("pgn") or "", ply)
        if board is None:
            continue
        seen_games.add(game_id)  # one drill per game keeps the three different
        items.append({
            "key": f"quest:{game_id}:{ply}",
            "source": "quest",
            "meta": f"this week's quest · {trait}",
            "title": title,
            "detail": f"vs {games[game_id].get('opponent') or 'your opponent'}, {move_label(ply, move.get('san'))}. {detail}",
            "fen": board.fen(),
            "answer": move["best_san"],
            "gameId": game_id,
            "ply": ply,
        })
        if len(items) == limit:
            break
    return items


def paged(build, game_ids: list[str], chunk: int = 20) -> list[dict]:
    """Every row for these games: ids in chunks, each chunk read in pages (PostgREST caps a response at 1,000)."""
    rows: list[dict] = []
    for start in range(0, len(game_ids), chunk):
        part = game_ids[start : start + chunk]
        got: list[dict] = []
        while True:
            batch = build(part).range(len(got), len(got) + 999).execute().data or []
            got += batch
            if len(batch) < 1000:
                break
        rows += got
    return rows


def moves_with_signal(game_ids: list[str], prefix: str) -> list[dict]:
    """Your moves in these games carrying a signal that starts with `prefix` (signals is jsonb: filtered here)."""
    rows = paged(lambda ids: get_supabase().table("game_moves").select("game_id, ply, signals").in_("game_id", ids).order("id"), game_ids)
    return [r for r in rows if any(str(sig).startswith(prefix) for sig in r.get("signals") or [])]


def board_before(pgn_text: str, ply: int) -> chess.Board | None:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return None
    board = game.board()
    for i, move in enumerate(game.mainline_moves()):
        if i == ply:
            return board
        board.push(move)
    return None


class QuestService:
    def quest(self, user_id: str | None, owner_id: str, focus: dict | None) -> dict | None:
        """This week's quest from the 3.2 focus: target, reference player, drills, how many you've answered."""
        if not focus:
            return None
        drills = quest_drills(user_id, focus["trait"])
        keys = [d["key"] for d in drills]
        done = 0
        if keys:
            rows = get_supabase().table("drill_reviews").select("drill_key").eq("owner_id", owner_id).in_("drill_key", keys).execute().data or []
            done = len({r["drill_key"] for r in rows})
        return {
            "trait": focus["trait"],
            "phrase": focus["phrase"],
            "value": focus["value"],
            "target": focus["target"],
            "unit": focus.get("unit", "share"),
            "reference": reference_for(focus["trait"], focus["value"]),
            "drills": drills,
            "done": done,
            "verdict": VERDICT.get(focus.get("verdict") or "held", "held"),
        }
