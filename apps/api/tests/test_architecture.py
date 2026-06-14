"""
Architecture tests — enforce module boundaries and project structure.

Guards the local-first monorepo layout defined in docs/ARCHITECTURE.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = API_ROOT / "app"
REPO_ROOT = API_ROOT.parents[1]
DOCS = REPO_ROOT / "docs"


def _py_files_under(relative: str) -> list[Path]:
    base = API_ROOT / relative
    return list(base.rglob("*.py")) if base.exists() else []


def _imports_in_file(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


class TestRepoDocs:
    """Gate 0 — philosophy and architecture docs must exist."""

    @pytest.mark.parametrize(
        "doc",
        [
            "PHILOSOPHY.md",
            "ARCHITECTURE.md",
            "PHASES.md",
            "QUALITY_GATES.md",
            "PRODUCT_SPEC.md",
            "CODE_REVIEW.md",
            "README.md",
        ],
    )
    def test_required_docs_exist(self, doc: str):
        assert (DOCS / doc).is_file(), f"Missing docs/{doc}"

    @pytest.mark.parametrize(
        "filename",
        ["LICENSE", "README.md", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md", "CODE_OF_CONDUCT.md"],
    )
    def test_root_docs_exist(self, filename: str):
        assert (REPO_ROOT / filename).is_file(), f"Missing {filename}"

    def test_adr_directory_exists(self):
        assert (DOCS / "adr").is_dir()
        assert (DOCS / "adr" / "0001-style-over-accuracy.md").is_file()


class TestModuleBoundaries:
    """Routers thin; services own logic; no Stockfish in HTTP layer."""

    def test_routers_do_not_import_chess_engine(self):
        banned = {"chess", "chess.engine"}
        violations = []
        for path in _py_files_under("app/routers"):
            imports = _imports_in_file(path)
            hit = imports & banned
            if hit:
                violations.append(f"{path.name}: {hit}")
        assert not violations, f"Routers must not use Stockfish directly: {violations}"

    def test_required_services_exist(self):
        required = [
            "chess_com.py",
            "move_classifier.py",
            "brilliant.py",
            "analysis.py",
            "baseline.py",
            "reference.py",
            "stockfish.py",
        ]
        services = APP_ROOT / "services"
        for name in required:
            assert (services / name).is_file(), f"Missing service: {name}"

    def test_config_centralizes_thresholds(self):
        config = (APP_ROOT / "config.py").read_text(encoding="utf-8")
        assert "brilliant_eval_margin" in config
        assert "brilliant_winning_margin" in config
        assert "local_user_id" in config


class TestSchemaMigration:
    """Database schema supports style-first data model."""

    def test_migration_includes_brilliant_and_style_vector(self):
        migrations = list((REPO_ROOT / "supabase" / "migrations").glob("*.sql"))
        assert migrations, "No migrations found"
        sql = "\n".join(m.read_text(encoding="utf-8") for m in migrations)
        assert "brilliant" in sql
        assert "style_vectors" in sql
        assert "reference_players" in sql
        assert "user_baselines" in sql


class TestGreptileConfig:
    """Gate 1.5 — Greptile foundation lock files must exist."""

    def test_root_greptile_config(self):
        greptile = REPO_ROOT / ".greptile"
        assert (greptile / "config.json").is_file()
        assert (greptile / "rules.md").is_file()
        assert (greptile / "files.json").is_file()

    def test_greptile_config_references_philosophy(self):
        config = (REPO_ROOT / ".greptile" / "config.json").read_text(encoding="utf-8")
        assert "foundation-no-remove-brilliant" in config
        assert "foundation-headline-brilliant-pct" in config
        assert "PHILOSOPHY" in config

    def test_greptile_files_json_includes_philosophy(self):
        files = (REPO_ROOT / ".greptile" / "files.json").read_text(encoding="utf-8")
        assert "PHILOSOPHY.md" in files
        assert "PRODUCT_SPEC.md" in files

    def test_scoped_greptile_configs_exist(self):
        assert (REPO_ROOT / "apps" / "api" / ".greptile" / "config.json").is_file()
        assert (REPO_ROOT / "apps" / "web" / ".greptile" / "config.json").is_file()


class TestNoMLInPhase1:
    """Phase 1 is rule-based — no ML frameworks."""

    BANNED = {"sklearn", "torch", "tensorflow", "keras", "xgboost"}

    def test_no_ml_imports_in_app(self):
        violations = []
        for path in _py_files_under("app"):
            imports = _imports_in_file(path)
            hit = imports & self.BANNED
            if hit:
                violations.append(f"{path.relative_to(API_ROOT)}: {hit}")
        assert not violations
