"""
Train (docs/DESIGN.md, screen 8): one queue drawn from your own games and the trap atlas, aimed
at the week's focus, with spaced review ("How sure were you?": Guessed → tomorrow, Unsure → 3
days, Sure → 9 days).

Sources available today:
- find the sacrifice: the engine's best move genuinely offered material and you played another;
- trap at your band: a trap atlas position near your opponents' ratings;
- play the other side: a sacrifice you played, to defend from the other chair.
The handoff's reference-game guess and saved video positions need data Sarce does not have yet,
so they are not invented here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import chess

from app.db.supabase import get_supabase
from app.services.home import HELD
from app.services.library import boards_before, real_offer
from app.services.summary import move_label

SPACING = {"guessed": 1, "unsure": 3, "sure": 9}
BANDS = list(range(800, 2400, 200))
QUEUE = 5


def _bare(san: str | None) -> str:
    return (san or "").rstrip("+#!?")


def check_move(fen: str, uci: str, answer: str | None, sacrifice_drill: bool, loss=None) -> dict:
    """
    Your move in a drill, checked on the server: its SAN, whether it is the drill's answer and,
    when it isn't, whether it still holds (within SAFE_TOL expected points of best, via `loss`).
    A "find the sacrifice" drill wants the sacrifice itself, so another sound move is "sound,
    but not the sacrifice". Raises ValueError on an illegal move.
    """
    from app.lenses.config import SAFE_TOL

    board = chess.Board(fen)
    move = chess.Move.from_uci(uci)
    if move not in board.legal_moves and len(uci) == 4:
        move = chess.Move.from_uci(uci + "q")  # auto-queen
    if move not in board.legal_moves:
        raise ValueError("illegal move")
    san = board.san(move)
    matched = bool(answer) and _bare(san) == _bare(answer)
    sound = None
    if not matched and loss is not None:
        try:
            sound = loss(board, move) <= SAFE_TOL
        except Exception:
            sound = None  # no engine: say only whether it matched
    if matched:
        line = "That's the move." if not sacrifice_drill else "That's the sacrifice."
    elif sound and sacrifice_drill:
        line = f"Sound, but not the sacrifice. {answer} was there."
    elif sound:
        line = f"That holds too. The engine's first choice was {answer}." if answer else "That holds."
    elif sound is False:
        line = f"That one lets the problem through. {answer} was the safe way." if answer else "That one lets the problem through."
    else:
        line = f"The answer was {answer}." if answer else "No answer stored for this one."
    return {"san": san, "uci": move.uci(), "matched": matched, "sound": sound, "line": line, "fen": _after(board, move)}


def _after(board: chess.Board, move: chess.Move) -> str:
    board.push(move)
    fen = board.fen()
    board.pop()
    return fen


def band_for(ratings: list[int]) -> int:
    """The atlas band nearest the average opponent rating (atlas bands start at 800)."""
    known = [r for r in ratings if r]
    if not known:
        return 1600
    avg = sum(known) / len(known)
    return min(BANDS, key=lambda b: abs(b + 100 - avg))


def next_due(confidence: str, now: datetime) -> datetime:
    if confidence not in SPACING:
        raise ValueError(f"confidence must be one of {list(SPACING)}")
    return now + timedelta(days=SPACING[confidence])


def missed_sacrifice(board: chess.Board, played: chess.Move, best_uci: str | None) -> chess.Move | None:
    """The engine's best move if it was a genuine offer and you played something else."""
    if not best_uci or best_uci == played.uci():
        return None
    try:
        best = chess.Move.from_uci(best_uci)
    except ValueError:
        return None
    if best not in board.legal_moves or real_offer(board, best) <= 0:
        return None
    return best


class TrainService:
    def queue(self, user_id: str | None, owner_id: str, focus: str | None) -> dict:
        sb = get_supabase()
        q = (
            sb.table("games")
            .select("id, played_at, opponent, opponent_rating, pgn")
            .eq("analysis_status", "complete")
            .order("played_at", desc=True)
            .limit(30)
        )
        if user_id:
            q = q.eq("user_id", user_id)
        games = q.execute().data or []
        due = self._not_due(owner_id)
        items: list[dict] = []

        ids = [g["id"] for g in games]
        moves = (
            sb.table("game_moves").select("game_id, ply, san, uci, best_uci, best_san, quality, signals").in_("game_id", ids).order("ply").execute().data
            if ids
            else []
        ) or []
        by_game: dict[str, list[dict]] = {}
        for m in moves:
            by_game.setdefault(m["game_id"], []).append(m)
        # The opponent's safe replies after each of your moves, from the chaos lens.
        safe: dict[tuple[str, int], list[str]] = {}
        if ids:
            for r in sb.table("move_lens_scores").select("game_id, ply, details").in_("game_id", ids).eq("lens", "chaos").execute().data or []:
                safe[(r["game_id"], r["ply"])] = (r.get("details") or {}).get("safe_set") or []

        missed, other_side = [], []
        for g in games:
            plies = boards_before(g.get("pgn") or "")
            for m in by_game.get(g["id"], []):
                if m["ply"] >= len(plies):
                    continue
                board, played = plies[m["ply"]]
                best = missed_sacrifice(board, played, m.get("best_uci"))
                if best is not None:
                    missed.append({
                        "key": f"find:{g['id']}:{m['ply']}",
                        "source": "find the sacrifice",
                        "meta": "from your games",
                        "title": "The sacrifice you didn't play",
                        "detail": f"vs {g.get('opponent') or 'your opponent'}, move {m['ply'] // 2 + 1}. A sound {m.get('best_san') or best.uci()} was there.",
                        "fen": board.fen(),
                        "answer": m.get("best_san") or best.uci(),
                        "gameId": g["id"],
                        "ply": m["ply"],
                    })
                elif (
                    m.get("quality") in HELD  # only sacrifices that held are worth defending
                    and "sacrifice" in (m.get("signals") or [])
                    and real_offer(board, played) > 0
                    and m["ply"] + 1 < len(plies)
                    and safe.get((g["id"], m["ply"]))
                ):
                    after, _ = plies[m["ply"] + 1]
                    try:
                        defence = after.san(chess.Move.from_uci(safe[(g["id"], m["ply"])][0]))
                    except ValueError:
                        continue
                    other_side.append({
                        "key": f"defend:{g['id']}:{m['ply']}",
                        "source": "play the other side",
                        "meta": "from your library",
                        "title": f"Defend your own {move_label(m['ply'], m.get('san'))}",
                        "detail": "You're the other side now. Find the reply your opponent needed.",
                        "fen": after.fen(),
                        "answer": defence,
                        "gameId": g["id"],
                        "ply": m["ply"] + 1,
                    })

        band = band_for([g.get("opponent_rating") for g in games])
        traps = sb.table("trap_atlas").select("fen_key, fen, band, eco, common_reply_uci, common_reply_share, best_reply_uci, frequency").eq("band", band).order("frequency", desc=True).limit(10).execute().data or []
        trap_items = []
        for t in traps:
            board = chess.Board(t["fen"])
            try:
                common = board.san(chess.Move.from_uci(t["common_reply_uci"]))
                best = board.san(chess.Move.from_uci(t["best_reply_uci"])) if t.get("best_reply_uci") else None
            except ValueError:
                continue
            trap_items.append({
                "key": f"trap:{t['fen_key']}:{band}",
                "source": "trap at your band",
                "meta": "trap atlas",
                "title": f"Skip the {common} trap" + (f" · {t['eco']}" if t.get("eco") else ""),
                "detail": f"{round(float(t.get('common_reply_share') or 0) * 100)}% of {band} players play {common} here and lose ground. Find the safe move.",
                "fen": t["fen"],
                "answer": best,
                "gameId": None,
                "ply": None,
            })

        # Interleave, putting the week's focus first, and skip drills not yet due.
        order = {"safe_reply": [trap_items, missed, other_side], "calm_after_sacrifice": [other_side, missed, trap_items]}.get(
            focus or "", [missed, trap_items, other_side]
        )
        pools = [[i for i in pool if i["key"] not in due] for pool in order]
        while len(items) < QUEUE and any(pools):
            for pool in pools:
                if pool and len(items) < QUEUE:
                    items.append(pool.pop(0))
        waiting = sum(len(p) for p in pools) + len(items)
        for item in items:
            item["legal"] = [m.uci() for m in chess.Board(item["fen"]).legal_moves]
        return {"band": band, "items": items, "waiting": waiting}

    def _not_due(self, owner_id: str) -> set[str]:
        """Drills answered recently enough that they are not due again yet."""
        now = datetime.now(timezone.utc).isoformat()
        rows = get_supabase().table("drill_reviews").select("drill_key").eq("owner_id", owner_id).gt("next_due", now).execute().data or []
        return {r["drill_key"] for r in rows}

    def answer(self, owner_id: str, drill_key: str, confidence: str) -> dict:
        now = datetime.now(timezone.utc)
        due = next_due(confidence, now)
        get_supabase().table("drill_reviews").insert(
            {"owner_id": owner_id, "drill_key": drill_key, "confidence": confidence, "next_due": due.isoformat(), "reviewed_at": now.isoformat()}
        ).execute()
        return {"drillKey": drill_key, "confidence": confidence, "nextDue": due.isoformat(), "inDays": SPACING[confidence]}
