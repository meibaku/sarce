"""Chaos, survival and soundness lenses — Chaos Lens M3. Hand-built fixtures, no engine."""

import ast
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.lenses import LensResult, PlyContext, PositionData, register, score_ply
from app.lenses.chaos import ChaosLens, position_chaos, split_safe
from app.lenses.registry import unregister
from app.lenses.survival import SurvivalLens
from app.main import app
from app.services.lens_service import (
    build_ply_contexts,
    keys_after_each_ply,
    objective_cost,
    score_contexts,
    summarize,
)

API_ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def position(eps: dict[str, float], probs: dict[str, float], complete: bool = True) -> PositionData:
    """A stored position: reply EPs (best first) and one probability table at Elo 1600."""
    lines = [{"move_uci": uci, "ep": ep} for uci, ep in eps.items()]
    return PositionData(lines=lines, safe_set_complete=complete, probs_by_elo={1600: probs})


# The opponent must recapture: a big cliff, but nearly everyone finds the move.
OBVIOUS_RECAPTURE = position(
    {"d8d5": 0.55, "a7a6": 0.15, "h7h6": 0.15}, {"d8d5": 0.92, "a7a6": 0.04, "h7h6": 0.04}
)
# Only one quiet move holds, and few players find it.
HIDDEN_ONLY_MOVE = position(
    {"g8h8": 0.50, "f8e8": 0.10, "d8d7": 0.08}, {"g8h8": 0.15, "f8e8": 0.50, "d8d7": 0.35}
)


def ctx(left=None, faced=None, **kwargs) -> PlyContext:
    defaults = {"ply": 20, "uci": "e4e5", "quality": "good", "ep_before": 0.5, "objective_cost": 0.0}
    return PlyContext(**{**defaults, **kwargs}, left=left, faced=faced, opponent_elo=1600)


class TestChaosFixtures:
    def test_obvious_recapture_is_low_chaos_despite_big_cliff(self):
        result = ChaosLens().score(ctx(left=OBVIOUS_RECAPTURE))
        assert result.details["stake"][1600] == pytest.approx(0.40)
        assert result.score < 0.10
        assert result.verdict is None

    def test_hidden_only_move_defence_is_high_chaos(self):
        result = ChaosLens().score(ctx(left=HIDDEN_ONLY_MOVE))
        assert result.details["p_fail"][1600] == pytest.approx(0.85)
        assert result.score > 0.30
        assert result.verdict == "real_chaos"
        assert result.details["safe_set"] == ["g8h8"]

    def test_already_won_position_scores_zero(self):
        result = ChaosLens().score(ctx(left=HIDDEN_ONLY_MOVE, ep_before=0.97))
        assert result.score == 0.0
        assert result.verdict is None
        assert result.details == {"decided": True}

    def test_cheap_chaos_is_high_chaos_from_a_losing_move(self):
        result = ChaosLens().score(ctx(left=HIDDEN_ONLY_MOVE, objective_cost=0.20))
        assert result.score > 0.30
        assert result.verdict == "cheap_chaos"

    def test_calculated_risk_sits_between(self):
        result = ChaosLens().score(ctx(left=HIDDEN_ONLY_MOVE, objective_cost=0.07))
        assert result.verdict == "calculated_risk"

    def test_no_stored_position_means_no_result(self):
        assert ChaosLens().score(ctx(left=None)) is None


class TestPositionChaos:
    def test_safe_set_uses_tolerance(self):
        safe, non_safe = split_safe([{"ep": 0.6}, {"ep": 0.56}, {"ep": 0.5}], 0.05)
        assert len(safe) == 2 and len(non_safe) == 1

    def test_all_replies_safe_means_nothing_at_stake(self):
        data = position_chaos(position({"a2a3": 0.5, "b2b3": 0.49}, {"a2a3": 0.5, "b2b3": 0.5}))
        assert data["stake"][1600] == 0.0 and data["chaos"][1600] == 0.0

    def test_reports_failure_mass_without_a_stored_eval(self):
        # 30% of replies are neither safe nor stored.
        data = position_chaos(position({"a2a3": 0.6, "b2b3": 0.2}, {"a2a3": 0.5, "b2b3": 0.2}))
        assert data["p_fail"][1600] == pytest.approx(0.5)
        assert data["unstored_mass"][1600] == pytest.approx(0.3)

    def test_nothing_to_compute_without_probabilities(self):
        assert position_chaos(PositionData(lines=[{"move_uci": "a2a3", "ep": 0.5}], safe_set_complete=True)) is None


class TestSurvival:
    def test_finding_the_only_move_is_survived(self):
        result = SurvivalLens().score(ctx(faced=HIDDEN_ONLY_MOVE, uci="g8h8"))
        assert (result.score, result.verdict) == (1.0, "survived")

    def test_missing_it_is_missed(self):
        result = SurvivalLens().score(ctx(faced=HIDDEN_ONLY_MOVE, uci="f8e8"))
        assert (result.score, result.verdict) == (0.0, "missed")

    def test_no_problem_set_means_no_result(self):
        assert SurvivalLens().score(ctx(faced=OBVIOUS_RECAPTURE, uci="d8d5")) is None


class TestRegistry:
    def test_default_lenses_run_together(self):
        results = score_ply(ctx(left=HIDDEN_ONLY_MOVE, faced=HIDDEN_ONLY_MOVE, uci="g8h8"))
        assert set(results) == {"soundness", "chaos", "survival"}

    def test_adding_a_lens_needs_no_engine_run(self):
        class DummyLens:
            name, version = "dummy", "1"

            def score(self, ply_ctx):
                return LensResult(float(ply_ctx.ply), "seen", {})

        contexts = [({"id": "move-1"}, ctx(left=HIDDEN_ONLY_MOVE))]
        register(DummyLens())
        try:
            # Any engine or human-model use during scoring would raise here.
            with patch("app.services.stockfish.StockfishEngine.__enter__", side_effect=AssertionError), \
                 patch("app.services.human_model.HeuristicHumanModel.move_probs", side_effect=AssertionError):
                rows = score_contexts("game-1", contexts)
        finally:
            unregister("dummy")
        dummy = [row for row in rows if row["lens"] == "dummy"]
        assert dummy == [
            {
                "game_id": "game-1", "game_move_id": "move-1", "ply": 20, "lens": "dummy",
                "lens_version": "1", "score": 20.0, "verdict": "seen", "details": {},
            }
        ]

    def test_lenses_never_import_engines(self):
        banned = {"app.services.stockfish", "app.services.human_model", "chess.engine"}
        for path in (API_ROOT / "app" / "lenses").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                assert not banned.intersection(names), f"{path.name} imports {names}"


class TestContextBuilding:
    PGN = "1. e4 e5 2. Nf3 *"

    def test_user_move_gets_the_positions_it_faced_and_left(self):
        keys = keys_after_each_ply(self.PGN)
        assert len(keys) == 3
        evals = {key: {"fen_key": key, "lines": [{"move_uci": "x", "ep": 0.5}], "safe_set_complete": True} for key in keys}
        probs = {keys[2]: {1600: {"x": 1.0}}}
        moves = [
            {"id": "m0", "ply": 0, "uci": "e2e4", "quality": "best", "cp_loss": 0, "eval_before": 0.2, "eval_after": 0.2},
            {"id": "m2", "ply": 2, "uci": "g1f3", "quality": "good", "cp_loss": 40, "eval_before": 0.3, "eval_after": -0.1},
        ]
        (_, first), (_, second) = build_ply_contexts(self.PGN, moves, evals, probs, 1500)
        assert first.faced is None and first.left is not None
        assert second.faced is not None and second.left.probs_by_elo == {1600: {"x": 1.0}}
        assert second.opponent_elo == 1500
        assert second.objective_cost > 0

    def test_objective_cost(self):
        assert objective_cost({"eval_after": 0.0, "cp_loss": 0}) == 0.0
        assert objective_cost({"eval_after": None, "cp_loss": 10}) is None
        assert 0.15 < objective_cost({"eval_after": -1.0, "cp_loss": 200}) < 0.5


class TestSummary:
    def test_counts_verdicts_and_survival_rate(self):
        rows = [
            {"lens": "chaos", "verdict": "real_chaos"},
            {"lens": "chaos", "verdict": "real_chaos"},
            {"lens": "chaos", "verdict": "cheap_chaos"},
            {"lens": "chaos", "verdict": None},
            {"lens": "survival", "verdict": "survived"},
            {"lens": "survival", "verdict": "missed"},
            {"lens": "soundness", "verdict": "best"},
        ]
        assert summarize(rows) == {
            "realChaos": 2, "cheapChaos": 1, "calculatedRisk": 0,
            "problemsFaced": 2, "survived": 1, "survivalRate": 0.5,
        }

    def test_no_problems_faced(self):
        assert summarize([])["survivalRate"] is None


class TestRoutes:
    @patch("app.routers.games.lens_service.get_game_lenses", return_value=[{"ply": 2, "lenses": {}}])
    def test_game_lenses(self, _mock):
        res = client.get("/games/abc/lenses")
        assert res.status_code == 200
        assert res.json() == {"gameId": "abc", "moves": [{"ply": 2, "lenses": {}}]}

    @patch("app.routers.games.lens_service.score_game", return_value=None)
    def test_refresh_unknown_game_is_404(self, _mock):
        assert client.get("/games/abc/lenses?refresh=true").status_code == 404

    @patch("app.routers.users.lens_service.chaos_summary")
    def test_chaos_summary_normalizes_username(self, mock_summary):
        mock_summary.return_value = {"username": "dratius", "realChaos": 1}
        res = client.get("/users/%20DRATIUS%20/chaos-summary")
        assert res.status_code == 200
        mock_summary.assert_called_once_with("dratius")

    def test_migration_enables_rls(self):
        sql = (API_ROOT.parents[1] / "supabase" / "migrations" / "20261010002000_move_lens_scores.sql").read_text(encoding="utf-8")
        assert "alter table public.move_lens_scores enable row level security" in sql
        assert "create policy" in sql
