"""Maia-2 adapter — tested with a stand-in for the optional `maia2` package."""

import sys
import time
import types
from concurrent.futures import ThreadPoolExecutor

import chess
import pytest

from app.services.human_model import get_human_model
from app.services.maia_model import Maia2HumanModel


def install_fake_maia2(monkeypatch, raw_probs):
    """Register a minimal `maia2` package that returns `raw_probs` for any position."""
    calls = {"loads": 0, "inferences": []}
    model = types.ModuleType("maia2.model")
    inference = types.ModuleType("maia2.inference")

    def from_pretrained(type, device, save_root):
        calls["loads"] += 1
        return f"model:{type}:{device}"

    def inference_each(loaded, prepared, fen, elo_self, elo_oppo):
        calls["inferences"].append((fen, elo_self, elo_oppo))
        return dict(raw_probs), 0.5

    model.from_pretrained = from_pretrained
    inference.prepare = lambda: "prepared"
    inference.inference_each = inference_each
    package = types.ModuleType("maia2")
    package.model, package.inference = model, inference
    for name, module in (("maia2", package), ("maia2.model", model), ("maia2.inference", inference)):
        monkeypatch.setitem(sys.modules, name, module)
    return calls


class TestMaia2Adapter:
    def test_registry_resolves_without_importing_the_package(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maia2", None)  # importing it would now fail
        model = get_human_model("maia2")
        assert isinstance(model, Maia2HumanModel)
        assert model.model_version == "maia2-0.11-blitz"

    def test_registry_shares_one_loaded_model_across_games(self, monkeypatch):
        monkeypatch.setattr("app.services.maia_model._shared", {})
        calls = install_fake_maia2(monkeypatch, {"e2e4": 1.0})
        for _game in range(3):
            get_human_model("maia2").move_probs(chess.Board(), 1500)
        assert get_human_model("maia2") is get_human_model("maia2")
        assert calls["loads"] == 1

    def test_checkpoint_instances_and_cache_versions_are_separate(self, monkeypatch):
        monkeypatch.setattr("app.services.maia_model._shared", {})
        blitz = get_human_model("maia2", "blitz")
        rapid = get_human_model("maia2", "rapid")
        assert blitz is get_human_model("maia2", "blitz")
        assert rapid is get_human_model("maia2", "rapid")
        assert blitz is not rapid
        assert blitz.model_version == "maia2-0.11-blitz"
        assert rapid.model_version == "maia2-0.11-rapid"

    def test_concurrent_first_use_loads_once(self, monkeypatch):
        calls = install_fake_maia2(monkeypatch, {"e2e4": 1.0})
        slow_load = sys.modules["maia2.model"].from_pretrained

        def from_pretrained(**kwargs):
            time.sleep(0.05)  # widen the window two unguarded threads would both fall into
            return slow_load(**kwargs)

        monkeypatch.setattr(sys.modules["maia2.model"], "from_pretrained", from_pretrained)
        model = Maia2HumanModel()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: model.move_probs(chess.Board(), 1500), range(4)))
        assert calls["loads"] == 1
        assert all(r["e2e4"] == pytest.approx(1.0) for r in results)

    def test_missing_package_gives_install_instructions(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maia2", None)
        with pytest.raises(RuntimeError, match="requirements-maia.txt"):
            Maia2HumanModel().move_probs(chess.Board(), 1500)

    def test_returns_a_normalized_probability_for_every_legal_move(self, monkeypatch):
        # The stand-in knows two legal moves and one illegal one, and does not sum to 1.
        install_fake_maia2(monkeypatch, {"e2e4": 0.6, "d2d4": 0.2, "e2e5": 0.2})
        board = chess.Board()
        probs = Maia2HumanModel().move_probs(board, 1500)
        assert set(probs) == {m.uci() for m in board.legal_moves}
        assert sum(probs.values()) == pytest.approx(1.0)
        assert probs["e2e4"] == pytest.approx(0.75) and probs["d2d4"] == pytest.approx(0.25)
        assert probs["g1f3"] == 0.0

    def test_loads_once_and_passes_the_rating_for_both_sides(self, monkeypatch):
        calls = install_fake_maia2(monkeypatch, {"e2e4": 1.0})
        model = Maia2HumanModel()
        model.move_probs(chess.Board(), 800)
        model.move_probs(chess.Board(), 2000)
        assert calls["loads"] == 1
        assert [(s, o) for _fen, s, o in calls["inferences"]] == [(800, 800), (2000, 2000)]

    def test_no_legal_moves_never_loads_the_model(self, monkeypatch):
        calls = install_fake_maia2(monkeypatch, {})
        mated = chess.Board("7k/5KQ1/8/8/8/8/8/8 b - - 0 1")
        assert Maia2HumanModel().move_probs(mated, 1500) == {}
        assert calls["loads"] == 0

    def test_all_zero_output_falls_back_to_uniform(self, monkeypatch):
        install_fake_maia2(monkeypatch, {})
        probs = Maia2HumanModel().move_probs(chess.Board(), 1500)
        assert sum(probs.values()) == pytest.approx(1.0) and len(set(probs.values())) == 1
