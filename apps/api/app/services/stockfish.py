"""
Stockfish UCI engine wrapper.

Reuses a single engine process per game analysis session for local performance.
See docs/ARCHITECTURE.md — Stockfish runs server-side only.
"""

from __future__ import annotations

import chess
import chess.engine

from app.config import settings


def score_to_pawns(score: chess.engine.Score, board: chess.Board) -> float | None:
    """Convert engine score to pawns from the perspective of the side to move."""
    if score is None:
        return None
    cp = score.pov(board.turn).score(mate_score=10000)
    return (cp / 100.0) if cp is not None else None


class StockfishEngine:
    """
    Context-managed Stockfish session.

    Usage:
        with StockfishEngine() as engine:
            best, eval = engine.analyze_position(board)
    """

    def __init__(self) -> None:
        self.path = settings.stockfish_executable
        self.depth = settings.analysis_depth
        self._engine: chess.engine.SimpleEngine | None = None

    def __enter__(self) -> StockfishEngine:
        self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        return self

    def __exit__(self, *args: object) -> None:
        if self._engine:
            self._engine.quit()
            self._engine = None

    def analyze_position(
        self, board: chess.Board
    ) -> tuple[chess.Move | None, float | None]:
        """Return best move and eval (pawns) for the side to move."""
        if not self._engine:
            raise RuntimeError("StockfishEngine must be used as a context manager")

        info = self._engine.analyse(board, chess.engine.Limit(depth=self.depth))
        score = info.get("score")
        pv = info.get("pv", [])
        best_move = pv[0] if pv else None
        eval_pawns = score_to_pawns(score, board) if score else None
        return best_move, eval_pawns

    def analyze_position_multipv(self, board: chess.Board, multipv: int = 3) -> list[dict]:
        """Return top engine candidates with evals from the side-to-move perspective."""
        if not self._engine:
            raise RuntimeError("StockfishEngine must be used as a context manager")

        infos = self._engine.analyse(
            board,
            chess.engine.Limit(depth=self.depth),
            multipv=multipv,
        )
        if isinstance(infos, dict):
            infos = [infos]

        candidates = []
        for info in infos:
            pv = info.get("pv", [])
            move = pv[0] if pv else None
            score = info.get("score")
            candidates.append(
                {
                    "move": move,
                    "eval": score_to_pawns(score, board) if score else None,
                }
            )
        return candidates

    def eval_after_move(
        self, board: chess.Board, move: chess.Move
    ) -> tuple[float | None, chess.Move | None]:
        """Eval after playing `move`, from the perspective of the player who moved."""
        board.push(move)
        best, eval_after = self.analyze_position(board)
        board.pop()
        # Flip eval to moving player's perspective
        if eval_after is not None:
            eval_after = -eval_after
        return eval_after, best
