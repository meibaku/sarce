"""
Sarce bots (docs/DESIGN.md, screen 9): games against Sarce itself, never assistance in a game on
another site. Stateless: every request carries the position as FEN, so the server keeps no game.

- Defender · 1600: plays like a human at the player's rating, but only among sound moves
  (within DEFENDER_TOL expected points of best), so sacrifices meet realistic replies.
- Tal-style attacker: among moves within TAL_TOL of best, plays the one that sets the hardest
  practical problem for a player at that rating (P_fail × stake, the chaos lens in reverse).
- Swindler: the same with a wider SWINDLE_TOL, for when it's behind and wants chances.

Repetition draws are not tracked (no move history is sent); everything else ends the game.
"""

from __future__ import annotations

import random
import threading

import chess

from app.lenses import config as lens_config
from app.services.human_model import get_human_model
from app.config import settings
from app.services.stockfish import StockfishEngine

BOTS = {
    "defender": "Defender · 1600",
    "tal": "Tal-style attacker",
    "swindler": "Swindler",
}
WHY = {
    "defender": "It defends like players at your rating, so your sacrifices meet realistic replies.",
    "tal": "It plays the sound move that sets you the hardest problem, the way Tal liked to.",
    "swindler": "It takes bigger risks to make you find the only move. Good practice for staying calm.",
}
DEFENDER_TOL, TAL_TOL, SWINDLE_TOL = 0.10, 0.15, 0.30
NODES = 60_000
CANDIDATES = 5


def status(board: chess.Board) -> str:
    if board.is_checkmate():
        return "checkmate"
    if board.is_stalemate():
        return "stalemate"
    if board.is_insufficient_material() or board.halfmove_clock >= 100:
        return "draw"
    return "ongoing"


def position_payload(board: chess.Board) -> dict:
    return {"fen": board.fen(), "legal": [m.uci() for m in board.legal_moves], "status": status(board), "turn": "white" if board.turn else "black"}


def p_fail_and_stake(replies: list[dict], probs: dict[str, float]) -> tuple[float, float]:
    """For the side to move: chance a human misses every safe reply, and what that costs them."""
    if not replies:
        return 0.0, 0.0
    best = replies[0]["ep"]
    safe = {r["move_uci"] for r in replies if r["ep"] >= best - lens_config.SAFE_TOL}
    p_safe = sum(p for uci, p in probs.items() if uci in safe)
    unsafe = [r for r in replies if r["move_uci"] not in safe]
    weight = sum(probs.get(r["move_uci"], 0) for r in unsafe)
    worse = sum(probs.get(r["move_uci"], 0) * r["ep"] for r in unsafe) / weight if weight else best
    return max(0.0, 1 - p_safe), max(0.0, best - worse)


def choose(bot: str, board: chess.Board, elo: int, engine, model, rng: random.Random) -> chess.Move:
    lines = engine.analyse(board, nodes=NODES, multipv=CANDIDATES)
    if not lines:
        return next(iter(board.legal_moves))
    best = lines[0]["ep"]
    if bot == "defender":
        sound = [l for l in lines if l["ep"] >= best - DEFENDER_TOL]
        probs = model.move_probs(board, elo)
        weights = [probs.get(l["move_uci"], 0.0) + 1e-6 for l in sound]
        return chess.Move.from_uci(rng.choices(sound, weights=weights)[0]["move_uci"])
    tol = TAL_TOL if bot == "tal" else SWINDLE_TOL
    scored = []
    for line in (l for l in lines if l["ep"] >= best - tol):
        move = chess.Move.from_uci(line["move_uci"])
        board.push(move)
        if board.is_checkmate():
            board.pop()
            return move
        replies = engine.analyse(board, nodes=NODES // 2, multipv=8) if not board.is_game_over() else []
        p_fail, stake = p_fail_and_stake(replies, model.move_probs(board, elo)) if replies else (0.0, 0.0)
        board.pop()
        scored.append((p_fail * stake + 0.001 * line["ep"], move))
    return max(scored, key=lambda s: s[0])[1] if scored else chess.Move.from_uci(lines[0]["move_uci"])


class BotService:
    """Keeps one engine open across moves: starting Stockfish per move cost seconds of bot clock."""

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self._engine: StockfishEngine | None = None
        self._lock = threading.Lock()

    def _choose(self, bot: str, board: chess.Board, elo: int) -> chess.Move:
        with self._lock:
            for attempt in range(2):
                try:
                    if self._engine is None:
                        self._engine = StockfishEngine().__enter__()
                    return choose(bot, board, elo, self._engine, get_human_model(settings.human_model), self.rng)
                except Exception:
                    # A crashed or stale engine: close it and retry once with a fresh one.
                    if self._engine is not None:
                        try:
                            self._engine.__exit__(None, None, None)
                        except Exception:
                            pass
                    self._engine = None
                    if attempt:
                        raise
        raise RuntimeError("unreachable")

    def close(self) -> None:
        """Stops the shared engine (called when the API shuts down)."""
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.__exit__(None, None, None)
                finally:
                    self._engine = None

    def start(self, color: str) -> dict:
        return position_payload(chess.Board())

    def move(self, fen: str, uci: str | None, bot: str, elo: int, reply: bool = True) -> dict:
        """
        Applies the player's move (if any), then, unless `reply` is false, the bot's reply. Sending the
        player's move with reply=false lets the board update at once while the bot thinks in a second call.
        Raises ValueError on an illegal move.
        """
        if bot not in BOTS:
            raise ValueError(f"bot must be one of {list(BOTS)}")
        board = chess.Board(fen)
        player_san = None
        if uci:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves and len(uci) == 4:
                move = chess.Move.from_uci(uci + "q")  # auto-queen
            if move not in board.legal_moves:
                raise ValueError("illegal move")
            player_san = board.san(move)
            board.push(move)
        bot_uci = bot_san = None
        if reply and status(board) == "ongoing":
            reply = self._choose(bot, board, elo)
            bot_uci, bot_san = reply.uci(), board.san(reply)
            board.push(reply)
        return {**position_payload(board), "playerSan": player_san, "botUci": bot_uci, "botSan": bot_san}
