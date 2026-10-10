"""Human move model interface and cache — Chaos Lens M2 (docs/CHAOS_PLAN.md)."""

from pathlib import Path

import chess
import pytest

from app.services.human_model import (
    ELO_LADDER,
    HeuristicHumanModel,
    HumanModel,
    cached_move_probs,
    elo_ladder,
    get_human_model,
)

MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"
# White can capture a queen, give check, or shuffle.
TACTICAL = "4k3/8/8/3q4/4P3/8/8/R3K3 w - - 0 1"


class FakeProbStore:
    def __init__(self):
        self.rows = {}

    def get(self, key, elo, model_version):
        return self.rows.get((key, elo, model_version))

    def put(self, row):
        self.rows[(row["fen_key"], row["elo"], row["model_version"])] = row


class CountingModel(HumanModel):
    name, version = "counting", "1"

    def __init__(self):
        self.calls = 0

    def move_probs(self, board, elo):
        self.calls += 1
        moves = [m.uci() for m in board.legal_moves]
        return {uci: 1 / len(moves) for uci in moves}


class TestEloLadder:
    def test_default_ladder(self):
        assert elo_ladder() == ELO_LADDER == [800, 1200, 1600, 2000, 2400]

    def test_adds_rounded_opponent_rating(self):
        assert elo_ladder(1487) == [800, 1200, 1500, 1600, 2000, 2400]

    def test_rating_already_on_the_ladder(self):
        assert elo_ladder(1620) == ELO_LADDER


class TestHeuristicModel:
    @pytest.mark.parametrize("elo", ELO_LADDER)
    def test_full_normalized_distribution(self, elo):
        board = chess.Board(TACTICAL)
        probs = HeuristicHumanModel().move_probs(board, elo)
        assert set(probs) == {m.uci() for m in board.legal_moves}
        assert sum(probs.values()) == pytest.approx(1.0)
        assert all(p > 0 for p in probs.values())

    def test_capturing_the_queen_is_the_most_likely_move(self):
        probs = HeuristicHumanModel().move_probs(chess.Board(TACTICAL), 1600)
        assert max(probs, key=probs.get) == "e4d5"

    def test_higher_elo_concentrates_on_the_natural_move(self):
        model, board = HeuristicHumanModel(), chess.Board(TACTICAL)
        assert model.move_probs(board, 2400)["e4d5"] > model.move_probs(board, 800)["e4d5"]

    def test_no_legal_moves(self):
        mated = chess.Board("7k/5KQ1/8/8/8/8/8/8 b - - 0 1")
        assert HeuristicHumanModel().move_probs(mated, 1600) == {}


class TestCache:
    def test_second_call_is_served_from_cache(self):
        model, store, board = CountingModel(), FakeProbStore(), chess.Board()
        first = cached_move_probs(board, 1600, model, store)
        second = cached_move_probs(board, 1600, model, store)
        assert model.calls == 1
        assert first == second

    def test_elo_and_model_version_are_part_of_the_key(self):
        model, store, board = CountingModel(), FakeProbStore(), chess.Board()
        cached_move_probs(board, 1200, model, store)
        cached_move_probs(board, 1600, model, store)
        model.version = "2"
        cached_move_probs(board, 1600, model, store)
        assert model.calls == 3 and len(store.rows) == 3

    def test_empty_distribution_is_not_cached(self):
        store = FakeProbStore()
        mated = chess.Board("7k/5KQ1/8/8/8/8/8/8 b - - 0 1")
        assert cached_move_probs(mated, 1600, CountingModelNoMoves(), store) == {}
        assert store.rows == {}


class CountingModelNoMoves(HumanModel):
    name, version = "empty", "1"

    def move_probs(self, board, elo):
        return {}


class TestRegistry:
    def test_default_model(self):
        assert get_human_model("heuristic").model_version == "heuristic-1"

    def test_unknown_model(self):
        with pytest.raises(ValueError):
            get_human_model("maia-9000")


class TestMigration:
    def test_human_probs_table_enables_rls(self):
        sql = (MIGRATIONS / "20261010001000_human_probs.sql").read_text(encoding="utf-8")
        assert "create table public.human_probs" in sql
        assert "alter table public.human_probs enable row level security" in sql
        assert "create policy" in sql
