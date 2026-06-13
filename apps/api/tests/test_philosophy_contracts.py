"""
Philosophy contract tests — enforce product invariants from docs/PHILOSOPHY.md.

These tests encode the north star: style is a goal, Brilliant % is headline.
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
    """Default Tal-style target: 6–10% Brilliant."""

    def test_default_target_band(self):
        empty = BaselineService._empty_baseline()
        assert empty["targetBrilliantMin"] == 6
        assert empty["targetBrilliantMax"] == 10

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


class TestDashboardContracts:
    """UI must surface Brilliant as headline, not hide it."""

    def test_brilliant_gauge_component_exists(self):
        assert (WEB_SRC / "components" / "brilliant-gauge.tsx").is_file()

    def test_dashboard_imports_brilliant_gauge(self):
        dashboard = (WEB_SRC / "components" / "dashboard.tsx").read_text(
            encoding="utf-8"
        )
        assert "BrilliantGauge" in dashboard
        assert "brilliantPct" in dashboard

    def test_style_summary_uses_encouraging_framing(self):
        summary = (WEB_SRC / "components" / "style-summary.tsx").read_text(
            encoding="utf-8"
        )
        # Must frame as target range, not failure language
        assert "target range" in summary.lower() or "Tal-style" in summary
        punitive = ["you failed", "bad player", "terrible", "shame"]
        for word in punitive:
            assert word not in summary.lower()


class TestPhilosophyDocAnchors:
    """PHILOSOPHY.md must contain core anchors for human + CI reference."""

    @pytest.fixture
    def philosophy(self) -> str:
        return (REPO_ROOT / "docs" / "PHILOSOPHY.md").read_text(encoding="utf-8")

    def test_mentions_brilliant_target(self, philosophy: str):
        assert "6" in philosophy and "10" in philosophy
        assert "Brilliant" in philosophy

    def test_mentions_style_over_accuracy(self, philosophy: str):
        assert re.search(r"style", philosophy, re.I)
        assert re.search(r"mirror.*not.*judge|not a judge", philosophy, re.I | re.S)

    def test_mentions_tal(self, philosophy: str):
        assert "Tal" in philosophy
