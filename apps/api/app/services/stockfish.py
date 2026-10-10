"""
Stockfish UCI engine wrapper.

Reuses a single engine process per game analysis session for local performance.
See docs/ARCHITECTURE.md — Stockfish runs server-side only.
"""

from __future__ import annotations

import chess
import chess.engine

from app.config import settings
from app.services.ep import line_ep


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
        # Output-only option: adds win/draw/loss to info lines without changing the search.
        if "UCI_ShowWDL" in self._engine.options:
            self._engine.configure({"UCI_ShowWDL": True})
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

    @property
    def engine_version(self) -> str:
        """Engine name as reported over UCI, stored with every cached evaluation."""
        if not self._engine:
            raise RuntimeError("StockfishEngine must be used as a context manager")
        return str(self._engine.id.get("name", "unknown"))

    def analyse(self, board: chess.Board, nodes: int, multipv: int) -> list[dict]:
        """
        Node-limited MultiPV search for the Chaos Lens (docs/CHAOS_PLAN.md, M1).

        Returns one dict per line, best first, from the side to move's perspective:
        `{move_uci, cp, mate, wdl, ep}`. Node limits (not depth or time) plus a fresh
        hash per call keep results reproducible.
        """
        if not self._engine:
            raise RuntimeError("StockfishEngine must be used as a context manager")

        infos = self._engine.analyse(
            board,
            chess.engine.Limit(nodes=nodes),
            multipv=multipv,
            # A new game object makes python-chess send `ucinewgame`, clearing the hash so
            # earlier searches in this session cannot change the result.
            game=object(),
        )
        lines = []
        for info in infos:
            pv = info.get("pv") or []
            score = info.get("score")
            if not pv or score is None:
                continue
            pov = score.pov(board.turn)
            wdl = info.get("wdl")
            wdl_counts = None
            if wdl is not None:
                side = wdl.pov(board.turn)
                wdl_counts = [side.wins, side.draws, side.losses]
            lines.append(
                {
                    "move_uci": pv[0].uci(),
                    "cp": pov.score(),
                    "mate": pov.mate(),
                    "wdl": wdl_counts,
                    "ep": line_ep(wdl_counts, pov.score(), pov.mate()),
                }
            )
        return lines

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
