"""
Opponent-aware chaos (implementation plan 3.7): where this opponent has gone wrong before.

From the scouted player's recent finished public games (the same fetch as the scouting report), the opening
positions they reach most often with them to move are checked with the engine: which replies they actually played
there, how much each gave away against the best reply (expected points), and how likely a player at their level is
to miss the safe set (P_fail, human model at their opponents' converted rating — the level they play at). The
positions where they went wrong most often come first.

Only the aggregate goes into the stored report (the position, the line to it, counts and the numbers), never the
games — the scouting privacy rules (services/scouting.py) are unchanged. Post-game only and public games only; the
report is built on request, never during a game.
"""

from __future__ import annotations

import io
import logging
from collections import Counter

import chess
import chess.pgn

from app.lenses.config import SAFE_TOL
from app.services.bots import p_fail_and_stake
from app.services.position_evals import fen_key
from app.services.rating_map import to_model_elo

logger = logging.getLogger(__name__)

MIN_PLY, MAX_PLY = 4, 20  # the opening stretch, past the first moves everyone plays
MIN_SEEN = 2
POSITIONS = 8  # checked with the engine
TOP = 5  # shown
NODES, LINES = 150_000, 6


def frequent_positions(parsed_games: list[dict]) -> list[dict]:
    """Positions with the scouted player to move, seen at least MIN_SEEN times: {fen, key, line, seen, replies}."""
    seen: dict[str, dict] = {}
    for parsed in parsed_games:
        game = chess.pgn.read_game(io.StringIO(parsed.get("pgn") or ""))
        color = parsed.get("user_color")
        if game is None or color not in ("white", "black"):
            continue
        player = chess.WHITE if color == "white" else chess.BLACK
        board, sans = game.board(), []
        for ply, move in enumerate(game.mainline_moves()):
            if ply >= MAX_PLY:
                break
            if board.turn == player and ply >= MIN_PLY:
                key = fen_key(board)
                entry = seen.setdefault(key, {"fen": board.fen(), "key": key, "line": " ".join(sans), "seen": 0, "replies": Counter()})
                entry["seen"] += 1
                entry["replies"][move.uci()] += 1
            sans.append(board.san(move))
            board.push(move)
    frequent = [e for e in seen.values() if e["seen"] >= MIN_SEEN]
    return sorted(frequent, key=lambda e: (-e["seen"], e["key"]))[:POSITIONS]


def their_level(parsed_games: list[dict], source: str) -> int:
    """The human-model rung for this player: their opponents' average rating, converted (they play at that level)."""
    ratings = [r for r in (to_model_elo(source, g.get("time_control"), g.get("opponent_rating")) for g in parsed_games) if r]
    avg = sum(ratings) / len(ratings) if ratings else 1500
    return int(round(avg / 100.0)) * 100


def score_position(entry: dict, engine, model, elo: int) -> dict | None:
    """Their record in one position: how often they went wrong, what it cost, and what holds."""
    board = chess.Board(entry["fen"])
    lines = engine.analyse(board, nodes=NODES, multipv=LINES)
    if not lines:
        return None
    best_ep, worst_ep = lines[0]["ep"], lines[-1]["ep"]
    ep_of = {ln["move_uci"]: ln["ep"] for ln in lines}
    wrong, lost, slips = 0, 0.0, Counter()
    for uci, n in entry["replies"].items():
        # A reply outside the engine's lines is at least as bad as the weakest line shown.
        loss = best_ep - ep_of.get(uci, worst_ep)
        if loss > SAFE_TOL:
            wrong += n
            lost += loss * n
            slips[uci] += n
    p_fail, _ = p_fail_and_stake(lines, model.move_probs(board, elo))
    slip = slips.most_common(1)[0][0] if slips else None
    return {
        "fen": entry["fen"],
        "line": entry["line"],
        "seen": entry["seen"],
        "wrong": wrong,
        "lostEp": round(lost / wrong, 3) if wrong else 0.0,
        "slip": board.san(chess.Move.from_uci(slip)) if slip else None,
        "best": board.san(chess.Move.from_uci(lines[0]["move_uci"])),
        "pFail": round(p_fail, 3),
        "elo": elo,
    }


def where_they_go_wrong(parsed_games: list[dict], source: str, engine, model) -> list[dict]:
    """Their most frequent opening positions, worst record first (times wrong, then what it cost)."""
    elo = their_level(parsed_games, source)
    out = []
    for entry in frequent_positions(parsed_games):
        try:
            scored = score_position(entry, engine, model, elo)
        except Exception:
            logger.exception("Opponent chaos: position skipped")
            continue
        if scored and scored["wrong"]:
            out.append(scored)
    return sorted(out, key=lambda s: (-s["wrong"] / s["seen"], -s["lostEp"]))[:TOP]
