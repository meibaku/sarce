"""Tests for centipawn loss → quality tier mapping."""

from app.services.move_classifier import (
    MoveQuality,
    centipawn_loss_to_quality,
    classify_move_quality,
    is_miss,
    is_user_ply,
)


class TestCentipawnLossToQuality:
    def test_best(self):
        assert centipawn_loss_to_quality(0) == MoveQuality.BEST

    def test_excellent(self):
        assert centipawn_loss_to_quality(20) == MoveQuality.EXCELLENT

    def test_good(self):
        assert centipawn_loss_to_quality(40) == MoveQuality.GOOD

    def test_inaccuracy(self):
        assert centipawn_loss_to_quality(80) == MoveQuality.INACCURACY

    def test_mistake(self):
        assert centipawn_loss_to_quality(150) == MoveQuality.MISTAKE

    def test_blunder(self):
        assert centipawn_loss_to_quality(500) == MoveQuality.BLUNDER


class TestMissDetection:
    def test_miss_when_winning_advantage_lost(self):
        assert is_miss(eval_before=2.0, eval_after=0.5, cp_loss=150) is True

    def test_not_miss_when_still_winning(self):
        assert is_miss(eval_before=2.0, eval_after=1.5, cp_loss=50) is False

    def test_not_miss_when_never_winning(self):
        assert is_miss(eval_before=0.5, eval_after=-1.0, cp_loss=150) is False


class TestClassifyMoveQuality:
    def test_miss_takes_priority_over_mistake(self):
        q = classify_move_quality(cp_loss=150, eval_before=2.0, eval_after=0.5)
        assert q == MoveQuality.MISS


class TestUserPly:
    def test_white_moves_on_even_plies(self):
        assert is_user_ply(0, "white") is True
        assert is_user_ply(1, "white") is False
        assert is_user_ply(2, "white") is True

    def test_black_moves_on_odd_plies(self):
        assert is_user_ply(1, "black") is True
        assert is_user_ply(0, "black") is False
        assert is_user_ply(3, "black") is True
