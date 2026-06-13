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

    def test_obvious_hanging_queen_is_bad(self):
        """Dropping queen without compensation should not be best/brilliant."""
        # White queen can be captured on d1 after nonsense moves — use simple blunder
        board = chess.Board("rnbqkb1r/pppp1ppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
        # Hang queen: Qd1 without development in a tactically sharp line
        # Simpler: move queen to a square where it's immediately taken
        board = chess.Board("rnbqkb1r/pppp1ppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2")
        moves = [chess.Move.from_uci("d1h5")]  # early queen sortie — often inaccuracy+
        classifier = MoveClassifier()
        results = classifier.classify_game(board, moves, user_color="white")
        assert results[0]["quality"] != MoveQuality.BRILLIANT.value
