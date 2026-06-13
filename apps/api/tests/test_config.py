"""Tests for Stockfish path resolution."""

from pathlib import Path

from app.config import resolve_stockfish_path


class TestResolveStockfishPath:
    def test_returns_file_path_directly(self, tmp_path: Path):
        exe = tmp_path / "stockfish.exe"
        exe.write_text("fake")
        assert resolve_stockfish_path(str(exe)) == str(exe)

    def test_finds_stockfish_exe_in_directory(self, tmp_path: Path):
        exe = tmp_path / "stockfish-windows-x86-64-avx2.exe"
        exe.write_text("fake")
        assert "stockfish" in resolve_stockfish_path(str(tmp_path)).lower()

    def test_returns_original_when_not_found(self):
        assert resolve_stockfish_path("/nonexistent/path") == "/nonexistent/path"
