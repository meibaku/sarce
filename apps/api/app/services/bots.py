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
import uuid
from datetime import datetime, timezone

import chess
import chess.pgn

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


RESULT_TAG = {"win": "1-0", "loss": "0-1", "draw": "1/2-1/2"}
BOT_TIME_CONTROL = "180"


def bot_game_pgn(moves: list[str], result: str, bot: str, clocks_ms: list[int] | None, played_at: datetime) -> str:
    """
    The PGN of a finished game against a Sarce bot (you play White), with %clk comments when the
    clocks were sent so the distraction check-ins can read your pace. Raises ValueError on an
    illegal move or an unknown result.
    """
    if result not in RESULT_TAG or bot not in BOTS:
        raise ValueError("unknown result or bot")
    game = chess.pgn.Game()
    game.headers.update({
        "Event": "Sarce bot game",
        "Site": "Sarce",
        "Date": played_at.strftime("%Y.%m.%d"),
        "White": "You",
        "Black": BOTS[bot],
        "Result": RESULT_TAG[result],
        "TimeControl": BOT_TIME_CONTROL,
    })
    node, board = game, chess.Board()
    for i, uci in enumerate(moves):
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            raise ValueError(f"illegal move {uci} at ply {i}")
        board.push(move)
        node = node.add_variation(move)
        if clocks_ms and i < len(clocks_ms) and clocks_ms[i] is not None:
            node.set_clock(max(0, clocks_ms[i]) / 1000)
    return str(game)


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

    def move_loss(self, board: chess.Board, move: chess.Move) -> float:
        """Expected points `move` gives up against the best move, for the side to move."""
        with self._lock:
            if self._engine is None:
                self._engine = StockfishEngine().__enter__()
            try:
                best = self._engine.analyse(board, nodes=NODES, multipv=1)
                board.push(move)
                try:
                    reply = self._engine.analyse(board, nodes=NODES, multipv=1) if not board.is_game_over() else []
                    after = 1 - reply[0]["ep"] if reply else (1.0 if board.is_checkmate() else 0.5)
                finally:
                    board.pop()
            except Exception:
                self._engine = None  # a crashed engine is replaced on the next call
                raise
        return max(0.0, (best[0]["ep"] if best else after) - after)

    def close(self) -> None:
        """Stops the shared engine (called when the API shuts down)."""
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.__exit__(None, None, None)
                finally:
                    self._engine = None

    def save(self, owner_id: str | None, bot: str, moves: list[str], result: str, clocks_ms: list[int] | None, elo: int) -> str:
        """Stores a finished bot game as a pending game (source sarce_bot) and returns its id."""
        from app.db.supabase import get_supabase

        now = datetime.now(timezone.utc)
        pgn = bot_game_pgn(moves, result, bot, clocks_ms, now)
        row = {
            "user_id": owner_id,
            "chess_com_username": "you",
            "external_id": f"sarce-bot:{uuid.uuid4()}",
            "source": "sarce_bot",
            "pgn": pgn,
            "played_at": now.isoformat(),
            "opponent": BOTS[bot],
            "opponent_rating": elo,
            "time_control": BOT_TIME_CONTROL,
            "result": result,
            "user_color": "white",
        }
        return get_supabase().table("games").insert(row).execute().data[0]["id"]

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
