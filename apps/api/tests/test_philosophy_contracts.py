"""
Philosophy contract tests — enforce product invariants from docs/PHILOSOPHY.md.

These tests encode the north star: style remains a legitimate goal while learning claims require evidence.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.baseline import BaselineService
from app.services.move_classifier import MoveQuality

REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"


class TestClassificationContracts:
    """Brilliant must be a first-class tier."""

    def test_brilliant_tier_exists(self):
        assert MoveQuality.BRILLIANT.value == "brilliant"

    def test_all_chess_com_tiers_exist(self):
        required = {
            "best", "excellent", "good", "inaccuracy",
            "mistake", "blunder", "miss", "brilliant",
        }
        assert {q.value for q in MoveQuality} == required

    def test_distribution_includes_brilliant_bucket(self):
        dist = BaselineService.compute_distribution(["brilliant", "best"])
        assert "brilliant" in dist
        assert dist["brilliant"] == 1


class TestTargetBandContracts:
    """Default Tal-style target: 0.2–0.6% Brilliant."""

    def test_default_target_band(self):
        empty = BaselineService._empty_baseline()
        assert empty["targetBrilliantMin"] == 0.2
        assert empty["targetBrilliantMax"] == 0.6

    def test_brilliant_pct_is_headline_metric(self):
        dist = {k: 0 for k in BaselineService.compute_distribution([])}
        dist.update({"brilliant": 1, "best": 9})
        assert BaselineService.brilliant_pct(dist) == 10.0


class TestStyleVectorContracts:
    """Style vectors are versioned — identity schema must not silently change."""

    def test_style_vector_v1_has_version(self):
        from app.services.analysis import build_style_vector_v1

        vec = build_style_vector_v1(
            BaselineService.compute_distribution(["best"]),
            0.0,
        )
        assert vec["version"] == 1
        assert "brilliantPct" in vec
        assert "distribution" in vec
        assert "sacrificeRate" in vec


class TestHomeContracts:
    """Home keeps the chosen Tal-style goal visible without turning it into universal progress."""

    def test_style_gauge_component_exists(self):
        assert (WEB_SRC / "components" / "ui" / "style-gauge.tsx").is_file()

    def test_home_shows_the_brilliant_gauge(self):
        home = (WEB_SRC / "components" / "home" / "home-view.tsx").read_text(encoding="utf-8")
        assert "StyleGauge" in home
        assert "Brilliant" in home

    def test_home_does_not_call_brilliant_universal_progress(self):
        home = (WEB_SRC / "components" / "home" / "home-view.tsx").read_text(encoding="utf-8").lower()
        assert "universal progress" not in home

    def test_home_gap_line_uses_encouraging_framing(self):
        from app.services.home import gap_line

        lines = [gap_line(None, 6, 10), gap_line(2.0, 6, 10), gap_line(8.0, 6, 10), gap_line(14.0, 6, 10)]
        punitive = ["you failed", "bad player", "terrible", "shame"]
        for line in lines:
            assert not any(word in line.lower() for word in punitive)
        home = (WEB_SRC / "components" / "home" / "home-view.tsx").read_text(encoding="utf-8").lower()
        assert not any(word in home for word in punitive)


class TestPhilosophyDocAnchors:
    """PHILOSOPHY.md must contain core anchors for human + CI reference."""

    @pytest.fixture
    def philosophy(self) -> str:
        return (REPO_ROOT / "docs" / "PHILOSOPHY.md").read_text(encoding="utf-8")

    def test_mentions_brilliant_target(self, philosophy: str):
        assert "0.2" in philosophy and "0.6" in philosophy
        assert "Brilliant" in philosophy

    def test_mentions_style_over_accuracy(self, philosophy: str):
        assert re.search(r"style", philosophy, re.I)
        assert re.search(r"mirror.*not.*judge|not a judge", philosophy, re.I | re.S)

    def test_mentions_tal(self, philosophy: str):
        assert "Tal" in philosophy

    def test_separates_style_from_learning(self, philosophy: str):
        assert "no universal progress score" in philosophy.lower()
        assert "recognised" in philosophy.lower()
        assert "retained" in philosophy.lower()
        assert "transferred" in philosophy.lower()

    def test_learning_protocol_is_preregistered(self):
        protocol = (REPO_ROOT / "docs" / "LEARNING_EVIDENCE_PROTOCOL.md").read_text(encoding="utf-8").lower()
        assert "primary endpoint" in protocol
        assert "day-7" in protocol
        assert "90%" in protocol
        assert "second learning" in protocol and "concept is added" in protocol
