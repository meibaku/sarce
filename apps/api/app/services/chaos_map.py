"""
Your chaos map: the positions you reach again and again, and the one sound move in each that sets the
hardest problem for players at your opponents' level.

At club level openings are predictable — the same Sicilian, the same Scotch gambit — so the useful
question is where, inside that predictable stretch, a single sound move asks the most of the opponent.
For each frequent position (you to move, first MAX_PLY plies of your games) the engine lists the sound
moves (within SOUND_TOL expected points of best); each is scored like the Tal-style bot: the chance a
player at the rating misses every safe reply (P_fail, human model) times what missing it costs (stake).
The best is compared with the move you usually play there. The map is rebuilt on request and stored
(`chaos_map`); everything is post-game, from your own finished games.
"""

from __future__ import annotations

import io
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone

import chess
import chess.pgn

from app.config import settings
from app.db.supabase import get_supabase
from app.services.bots import p_fail_and_stake
from app.services.position_evals import fen_key
from app.services.review import LADDER

logger = logging.getLogger(__name__)

MAX_PLY = 16  # the opening stretch where play is most predictable
MIN_PLY = 3  # skip the first move or two: everyone plays them
MIN_SEEN = 4  # a position must come up at least this often
TOP_POSITIONS = 8
SOUND_TOL = 0.08  # expected points from best that still counts as sound
NODES, REPLY_NODES = 200_000, 100_000
CANDIDATES, REPLIES = 6, 8
GAMES_READ = 800
CHAOS_DRILL = "chaos move in your opening"  # the Train source name; /train/check keys off it
RATING_GAMES = 100  # newest games only: the rung should follow your current level


def opening_positions(games: list[dict]) -> list[dict]:
    """
    The most frequent positions with you to move: {fen, key, seen, line, usual, usualCount,
    predictability}. `predictability` is how often opponents, in the position just before, played
    the move that leads here — high means you can count on reaching it.
    """
    seen: dict[str, dict] = {}
    opp_moves: dict[str, Counter] = defaultdict(Counter)  # opponent-to-move key -> moves played there
    for g in games:
        game = chess.pgn.read_game(io.StringIO(g.get("pgn") or ""))
        if game is None:
            continue
        you = chess.WHITE if g.get("user_color") == "white" else chess.BLACK
        board, sans, came_from = game.board(), [], None
        for ply, move in enumerate(game.mainline_moves()):
            if ply >= MAX_PLY:
                break
            key = fen_key(board)
            if board.turn == you:
                if ply >= MIN_PLY:
                    entry = seen.setdefault(key, {"fen": board.fen(), "key": key, "seen": 0, "line": " ".join(sans), "moves": Counter(), "via": Counter()})
                    entry["seen"] += 1
                    entry["moves"][move.uci()] += 1
                    if came_from:
                        entry["via"][came_from] += 1
            else:
                opp_moves[key][move.uci()] += 1
                came_from = (key, move.uci())
            sans.append(board.san(move))
            board.push(move)

    out = []
    for entry in seen.values():
        if entry["seen"] < MIN_SEEN:
            continue
        predictability = None
        if entry["via"]:
            (parent, uci), _ = entry["via"].most_common(1)[0]
            counts = opp_moves[parent]
            predictability = round(counts[uci] / sum(counts.values()), 3)
        usual, usual_n = entry["moves"].most_common(1)[0]
        out.append({**{k: entry[k] for k in ("fen", "key", "seen", "line")}, "usual": usual, "usualCount": usual_n, "predictability": predictability})
    # Most often reached first; among equals, the deeper position (more of the opening decided).
    out.sort(key=lambda e: (-e["seen"], -len(e["line"])))
    return out[:TOP_POSITIONS]


def score_move(board: chess.Board, move: chess.Move, engine, model, elo: int) -> dict:
    """P_fail × stake for the opponent after `move` (the Tal bot's measure)."""
    board.push(move)
    try:
        if board.is_game_over():
            return {"pFail": 0.0, "stake": 0.0, "score": 0.0}
        lines = engine.analyse(board, nodes=REPLY_NODES, multipv=REPLIES)
        p_fail, stake = p_fail_and_stake(lines, model.move_probs(board, elo)) if lines else (0.0, 0.0)
    finally:
        board.pop()
    return {"pFail": round(p_fail, 3), "stake": round(stake, 3), "score": round(p_fail * stake, 4)}


def chaos_move(position: dict, engine, model, elo: int) -> dict | None:
    """The sound move with the highest P_fail × stake here, and how your usual move compares."""
    board = chess.Board(position["fen"])
    lines = engine.analyse(board, nodes=NODES, multipv=CANDIDATES)
    if not lines:
        return None
    best_ep = lines[0]["ep"]
    scored = []
    for ln in lines:
        if ln["ep"] < best_ep - SOUND_TOL:
            continue
        move = chess.Move.from_uci(ln["move_uci"])
        scored.append({"uci": ln["move_uci"], "san": board.san(move), "epLoss": round(best_ep - ln["ep"], 3), **score_move(board, move, engine, model, elo)})
    top = max(scored, key=lambda s: s["score"])
    usual = next((s for s in scored if s["uci"] == position["usual"]), None)
    if usual is None:
        # Your usual move is outside the sound set (or past the engine's top lines): score it anyway.
        move = chess.Move.from_uci(position["usual"])
        ep = next((ln["ep"] for ln in lines if ln["move_uci"] == position["usual"]), None)
        usual = {"uci": move.uci(), "san": board.san(move), "epLoss": None if ep is None else round(best_ep - ep, 3), **score_move(board, move, engine, model, elo)}
    return {"chaos": top, "usual": usual}


def opponent_rung(games: list[dict]) -> int:
    """The human-model rung nearest your recent opponents' average rating (1200 when unknown)."""
    ratings = [g["opponent_rating"] for g in games[:RATING_GAMES] if g.get("opponent_rating")]
    avg = sum(ratings) / len(ratings) if ratings else 1200
    return min(LADDER, key=lambda r: abs(r - avg))


def problem(p_fail: float | None, stake: float | None) -> float | None:
    """Expected points an opponent drops facing the move: P_fail × stake (what the map ranks by)."""
    return None if p_fail is None or stake is None else round(p_fail * stake, 3)


WORTH_IT = 0.02  # expected points: below this gain the chaos move is not worth changing a habit for


def drill_items(positions: list[dict]) -> list[dict]:
    """Train drills: positions where the chaos move sets a clearly bigger problem than your usual move."""
    items = []
    for p in positions:
        gain = (p["chaos"]["problem"] or 0) - (p["usual"]["problem"] or 0)
        if p["same"] or gain < WORTH_IT:
            continue
        items.append({
            "key": f"chaos:{p['key']}",
            "source": CHAOS_DRILL,
            "meta": "your chaos map",
            "title": f"After {p['line']}",
            "detail": f"You reach this {p['seen']}× and usually play {p['usual']['san']}. Find the sound move that asks your opponent the most.",
            "fen": p["fen"],
            "answer": p["chaos"]["san"],
            "gameId": None,
            "ply": None,
            "_gain": gain,
        })
    items.sort(key=lambda i: -i.pop("_gain"))
    return items


def to_api(row: dict) -> dict:
    return {
        "key": row["fen_key"],
        "fen": row["fen"],
        "line": row["line"],
        "seen": row["seen"],
        "predictability": row["predictability"],
        "usual": {"san": row["usual_move"], "pFail": row["usual_p_fail"], "stake": row["usual_stake"], "problem": problem(row["usual_p_fail"], row["usual_stake"])},
        "chaos": {"san": row["chaos_move"], "uci": row["chaos_uci"], "pFail": row["chaos_p_fail"], "stake": row["chaos_stake"], "epLoss": row["chaos_ep_loss"], "problem": problem(row["chaos_p_fail"], row["chaos_stake"])},
        "same": row["usual_move"] == row["chaos_move"],
        "elo": row["elo"],
        "computedAt": row["computed_at"],
    }


class ChaosMapService:
    def build(self, owner_id: str) -> dict:
        """Recomputes the owner's map (engine work: a minute or two) and replaces the stored one."""
        from app.services.human_model import get_human_model
        from app.services.stockfish import StockfishEngine

        sb = get_supabase()
        games = (
            sb.table("games").select("pgn, user_color, opponent_rating").eq("user_id", owner_id).neq("source", "sarce_bot")
            .order("played_at", desc=True).limit(GAMES_READ).execute().data
            or []
        )
        positions = opening_positions(games)
        elo = opponent_rung(games)
        model = get_human_model(settings.human_model)
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        with StockfishEngine() as engine:
            for pos in positions:
                try:
                    found = chaos_move(pos, engine, model, elo)
                except Exception:
                    logger.exception("Chaos map failed at %s", pos["key"])
                    continue
                if not found:
                    continue
                c, u = found["chaos"], found["usual"]
                rows.append({
                    "user_id": owner_id, "fen": pos["fen"], "fen_key": pos["key"], "line": pos["line"],
                    "seen": pos["seen"], "predictability": pos["predictability"],
                    "usual_move": u["san"], "usual_p_fail": u["pFail"], "usual_stake": u["stake"],
                    "chaos_move": c["san"], "chaos_uci": c["uci"], "chaos_p_fail": c["pFail"],
                    "chaos_stake": c["stake"], "chaos_ep_loss": c["epLoss"], "elo": elo, "computed_at": now,
                })
        sb.table("chaos_map").delete().eq("user_id", owner_id).execute()
        if rows:
            sb.table("chaos_map").insert(rows).execute()
        return {"positions": len(rows), "elo": elo}

    def get(self, owner_id: str) -> list[dict]:
        rows = get_supabase().table("chaos_map").select("*").eq("user_id", owner_id).order("seen", desc=True).execute().data or []
        return [to_api(r) for r in rows]
