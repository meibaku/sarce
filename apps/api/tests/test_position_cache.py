"""Position evaluation cache — Chaos Lens M1 (docs/CHAOS_PLAN.md). No engine or database needed."""

from pathlib import Path

import chess

from app.services.pgn_parser import extract_clocks_ms
from app.services.position_evals import (
    evaluate_game_positions,
    evaluate_position,
    fen_key,
    mover_ep_before,
    safe_set_complete,
)

MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"


class FakeStore:
    def __init__(self):
        self.rows = {}

    def get(self, key, nodes):
        return self.rows.get((key, nodes))

    def put(self, row):
        self.rows[(row["fen_key"], row["nodes"])] = row


class FakeEngine:
    """Returns `eps[:multipv]` as lines and records every call."""

    engine_version = "Fake 1.0"

    def __init__(self, eps):
        self.eps = eps
        self.calls = []

    def analyse(self, board, nodes, multipv):
        self.calls.append(multipv)
        moves = [m.uci() for m in board.legal_moves]
        return [
            {"move_uci": uci, "cp": 0, "mate": None, "wdl": None, "ep": ep}
            for uci, ep in zip(moves, self.eps[:multipv])
        ]


def evaluate(board, engine, store, **kwargs):
    params = {"nodes": 1000, "multipv": 4, "multipv_cap": 8, "safe_tol": 0.05}
    return evaluate_position(board, engine, store, **{**params, **kwargs})


class TestFenKey:
    def test_drops_only_the_fullmove_number(self):
        board = chess.Board("8/8/4k3/8/8/4K3/4P3/8 w - - 12 40")
        assert fen_key(board) == "8/8/4k3/8/8/4K3/4P3/8 w - - 12"

    def test_halfmove_clock_separates_positions(self):
        early = chess.Board("8/8/4k3/8/8/4K3/4P3/8 w - - 3 40")
        late = chess.Board("8/8/4k3/8/8/4K3/4P3/8 w - - 98 90")
        assert fen_key(early) != fen_key(late)


class TestEvaluatePosition:
    def test_cache_hit_avoids_engine_call(self):
        store, board = FakeStore(), chess.Board()
        first_engine = FakeEngine([0.55, 0.5, 0.45, 0.4])
        first = evaluate(board, first_engine, store)

        second_engine = FakeEngine([0.9, 0.1, 0.1, 0.1])
        second = evaluate(board, second_engine, store)

        assert first_engine.calls == [4]
        assert second_engine.calls == []
        assert second == first

    def test_stops_when_last_line_is_outside_tolerance(self):
        engine = FakeEngine([0.60, 0.58, 0.57, 0.40])
        row = evaluate(chess.Board(), engine, FakeStore())
        assert engine.calls == [4]
        assert row["multipv"] == 4
        assert row["safe_set_complete"] is True

    def test_widens_until_safe_set_is_complete(self):
        engine = FakeEngine([0.60, 0.59, 0.58, 0.57, 0.56, 0.30, 0.2, 0.1])
        row = evaluate(chess.Board(), engine, FakeStore())
        assert engine.calls == [4, 8]
        assert row["multipv"] == 8
        assert row["safe_set_complete"] is True

    def test_cap_marks_safe_set_incomplete(self):
        engine = FakeEngine([0.5] * 20)
        row = evaluate(chess.Board(), engine, FakeStore())
        assert engine.calls == [4, 8]
        assert row["safe_set_complete"] is False

    def test_never_asks_for_more_lines_than_legal_moves(self):
        # Black is in check with exactly two legal replies.
        board = chess.Board("7k/8/8/8/8/8/K7/7R b - - 0 1")
        assert board.legal_moves.count() == 2
        engine = FakeEngine([0.5, 0.5])
        row = evaluate(board, engine, FakeStore())
        assert engine.calls == [2]
        assert row["safe_set_complete"] is True

    def test_terminal_position_is_not_evaluated(self):
        mated = chess.Board("7k/5KQ1/8/8/8/8/8/8 b - - 0 1")
        assert mated.is_checkmate()
        engine, store = FakeEngine([0.5]), FakeStore()
        assert evaluate(mated, engine, store) is None
        assert engine.calls == [] and store.rows == {}


class TestSafeSetComplete:
    def test_missing_ep_is_incomplete(self):
        assert not safe_set_complete([{"ep": 0.6}, {"ep": None}], 0.05)

    def test_gap_larger_than_tolerance_is_complete(self):
        assert safe_set_complete([{"ep": 0.6}, {"ep": 0.5}], 0.05)


class TestGamePositions:
    MOVES = [chess.Move.from_uci(u) for u in ("e2e4", "e7e5", "g1f3", "b8c6")]

    def test_mover_ep_before_uses_phase1_evals(self):
        phase1 = {0: {"eval_before": 0.0, "eval_after": 2.0}}
        assert mover_ep_before(0, "white", phase1) == 0.5
        # Opponent ply mirrors the user's eval after the previous move.
        assert mover_ep_before(1, "white", phase1) < 0.5
        assert mover_ep_before(3, "white", phase1) is None

    def test_evaluates_positions_after_both_players_moves(self):
        classified = [
            {"ply": 0, "eval_before": 0.2, "eval_after": 0.2},
            {"ply": 2, "eval_before": 0.1, "eval_after": 0.3},
        ]
        engine, store = FakeEngine([0.6, 0.4, 0.3, 0.2]), FakeStore()
        stats = evaluate_game_positions(
            chess.Board(), self.MOVES, "white", classified, engine, store
        )
        assert stats == {"evaluated": 4, "skipped_decided": 0, "terminal": 0}
        assert len(store.rows) == 4

    def test_skips_plies_from_decided_positions(self):
        # White is completely winning before ply 2, so plies 2 and 3 are skipped.
        classified = [
            {"ply": 0, "eval_before": 0.2, "eval_after": 0.2},
            {"ply": 2, "eval_before": 15.0, "eval_after": 15.0},
        ]
        engine, store = FakeEngine([0.6, 0.4, 0.3, 0.2]), FakeStore()
        stats = evaluate_game_positions(
            chess.Board(), self.MOVES, "white", classified, engine, store
        )
        assert stats == {"evaluated": 2, "skipped_decided": 2, "terminal": 0}

    def test_second_run_is_served_from_cache(self):
        classified = [{"ply": 0, "eval_before": 0.2, "eval_after": 0.2}]
        store = FakeStore()
        evaluate_game_positions(
            chess.Board(), self.MOVES, "white", classified, FakeEngine([0.6, 0.4, 0.3, 0.2]), store
        )
        stored = dict(store.rows)
        rerun = FakeEngine([0.1, 0.1, 0.1, 0.1])
        evaluate_game_positions(chess.Board(), self.MOVES, "white", classified, rerun, store)
        assert rerun.calls == []
        assert store.rows == stored


class TestClockParsing:
    PGN = (
        '[Event "Live Chess"]\n[TimeControl "60"]\n\n'
        "1. e4 {[%clk 0:00:59.9]} 1... e5 {[%clk 0:00:58.4]} "
        "2. Nf3 {[%clk 0:00:57]} 2... Nc6 *"
    )

    def test_one_clock_per_ply_in_milliseconds(self):
        assert extract_clocks_ms(self.PGN) == [59900, 58400, 57000, None]

    def test_pgn_without_clocks(self):
        assert extract_clocks_ms("1. e4 e5 *") == [None, None]

    def test_unparseable_pgn(self):
        assert extract_clocks_ms("") == []


class TestMigration:
    def test_position_evals_table_enables_rls(self):
        sql = (MIGRATIONS / "20261010000000_position_evals.sql").read_text(encoding="utf-8")
        assert "create table public.position_evals" in sql
        assert "alter table public.position_evals enable row level security" in sql
        assert "create policy" in sql
        assert "clocks_ms" in sql
