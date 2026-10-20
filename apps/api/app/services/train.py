"""
Train (docs/DESIGN.md, screen 8): one queue drawn from your own games and the trap atlas, aimed
at the week's focus, with spaced review ("How sure were you?": Guessed → tomorrow, Unsure → 3
days, Sure → 9 days).

Sources available today:
- find the sacrifice: the engine's best move genuinely offered material and you played another;
- trap at your band: a trap atlas position near your opponents' ratings;
- play the other side: a sacrifice you played, to defend from the other chair;
- a saved position: one you kept from Review ("Add to Train"), services/positions.py;
- Tal in your openings: a position from a Tal game with an ECO you play, where you guess his move
  (data/reference_positions.json). Traps from your own openings are also put first.
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


def check_move(fen: str, uci: str, answer: str | None, sacrifice_drill: bool, loss=None, reference_drill: bool = False) -> dict:
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
    if reference_drill:
        # The answer is what Tal played, not the engine's choice: say so.
        line = (
            "That's what Tal played."
            if matched
            else f"That holds too. Tal played {answer}."
            if sound
            else f"That one lets the problem through. Tal played {answer}."
            if sound is False
            else f"Tal played {answer}."
        )
    elif matched:
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


def your_openings(user_id: str | None, top: int = 5) -> list[str]:
    """Your most played ECO codes, most played first (games.eco, migration game_openings)."""
    q = get_supabase().table("games").select("eco").neq("source", "sarce_bot").order("played_at", desc=True).limit(500)
    if user_id:
        q = q.eq("user_id", user_id)
    counts: dict[str, int] = {}
    for row in q.execute().data or []:
        if row.get("eco"):
            counts[row["eco"]] = counts.get(row["eco"], 0) + 1
    return sorted(counts, key=lambda e: -counts[e])[:top]


def reference_items(ecos: list[str], seed: int) -> list[dict]:
    """ "Tal in your openings": guess Tal's move in a position from a Tal game in an opening you play."""
    from app.services.reference_axes import in_your_openings, reference_positions

    picks = in_your_openings(reference_positions().get("Tal", []), ecos, seed)
    return [
        {
            "key": f"tal:{p['eco']}:{p['fen']}",
            "source": "Tal in your openings",
            "meta": f"{p.get('year') or 'Tal'} · {p['eco']}",
            "title": "What did Tal play here?",
            "detail": f"Tal vs {p.get('opponent') or 'opponent'}{', ' + p['event'] if p.get('event') else ''}, from the {p['eco']} family you play. Find his move.",
            "fen": p["fen"],
            "answer": p["san"],
            "gameId": None,
            "ply": None,
        }
        for p in picks
    ]


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
    def queue(self, user_id: str | None, owner_id: str, focus: str | None, first: str | None = None) -> dict:
        """The queue; `first` (a drill key, e.g. from the library's "Defend it yourself") goes to the front."""
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
        ecos = your_openings(user_id)
        traps = sb.table("trap_atlas").select("fen_key, fen, band, eco, common_reply_uci, common_reply_share, best_reply_uci, frequency").eq("band", band).order("frequency", desc=True).limit(40).execute().data or []
        # Traps in your own openings first (exact ECO, then family), then the band's most common.
        rank = {eco: i for i, eco in enumerate(ecos)}
        traps = sorted(traps, key=lambda t: (rank.get(t.get("eco"), len(rank) + (0 if any((t.get("eco") or "")[:2] == e[:2] for e in ecos) else 1)), -(t.get("frequency") or 0)))[:10]
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

        from app.services.positions import PositionStore, drill_items

        saved = drill_items(PositionStore().list(owner_id))
        tal = reference_items(ecos, datetime.now(timezone.utc).date().toordinal())
        # Interleave, putting the week's focus first, and skip drills not yet due.
        order = {"safe_reply": [trap_items, missed, other_side, tal, saved], "calm_after_sacrifice": [other_side, missed, trap_items, tal, saved]}.get(
            focus or "", [missed, trap_items, tal, other_side, saved]
        )
        wanted = next((i for pool in order for i in pool if i["key"] == first), None) if first else None
        pools = [[i for i in pool if i["key"] not in due and i is not wanted] for pool in order]
        if wanted:
            items.append(wanted)
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
