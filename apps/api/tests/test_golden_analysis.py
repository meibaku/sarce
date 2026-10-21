"""
Golden analysis tests — Stockfish tier regression (local only).

Run with Stockfish installed:
    pytest tests/test_golden_analysis.py -m stockfish -v

Skipped in CI when STOCKFISH_PATH is unavailable.
"""

from __future__ import annotations

from pathlib import Path

import chess
import chess.pgn
import pytest

from app.config import resolve_stockfish_path, settings
from app.services.move_classifier import MoveClassifier, MoveQuality

FIXTURES = Path(__file__).parent / "fixtures"


def stockfish_available() -> bool:
    path = resolve_stockfish_path(settings.stockfish_path)
    return Path(path).is_file()


pytestmark = pytest.mark.stockfish


@pytest.mark.skipif(not stockfish_available(), reason="Stockfish binary not found")
class TestGoldenAnalysis:
    """Stable positions must classify consistently across threshold tweaks."""

    def test_starting_e4_is_reasonable(self):
        """Opening e4 should not be blunder/miss for white."""
        board = chess.Board()
        moves = [chess.Move.from_uci("e2e4")]
        classifier = MoveClassifier()
        results = classifier.classify_game(board, moves, user_color="white")
        assert len(results) == 1
        assert results[0]["quality"] in {
            MoveQuality.BEST.value,
            MoveQuality.EXCELLENT.value,
            MoveQuality.GOOD.value,
            MoveQuality.BRILLIANT.value,
        }

    def test_early_queen_sortie_is_not_brilliant(self):
        """An early queen sortie should never be classified as brilliant."""
        # After 1. e4 e5, the early queen sortie 2. Qh5 is legal and never a sacrifice.
        # (The previous fixture had a pawn on e2, so d1h5 was illegal and crashed the engine.)
        board = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
        moves = [chess.Move.from_uci("d1h5")]
        assert moves[0] in board.legal_moves
        classifier = MoveClassifier()
        results = classifier.classify_game(board, moves, user_color="white")
        assert results[0]["quality"] != MoveQuality.BRILLIANT.value

    def test_node_limited_search_is_deterministic(self):
        """Chaos Lens M1: the same position searched twice must give identical lines."""
        from app.services.stockfish import StockfishEngine

        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        with StockfishEngine() as engine:
            first = engine.analyse(board, nodes=200_000, multipv=4)
            engine.analyse(chess.Board(), nodes=50_000, multipv=2)  # disturb the hash
            second = engine.analyse(board, nodes=200_000, multipv=4)
        assert len(first) == 4
        assert all(0.0 <= line["ep"] <= 1.0 for line in first)
        assert first == second
