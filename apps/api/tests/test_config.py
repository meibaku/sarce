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


def test_prefers_the_fastest_build_that_runs(tmp_path: Path):
    for arch in ("x86-64", "x86-64-avx2", "x86-64-avx512", "x86-64-bmi2"):
        (tmp_path / f"stockfish-windows-{arch}.exe").write_text("fake")
    assert resolve_stockfish_path(str(tmp_path)).endswith("avx512.exe")
    # avx512 dies on this CPU: the next fastest that runs wins.
    assert resolve_stockfish_path(str(tmp_path), probe=lambda exe: "avx512" not in exe).endswith("avx2.exe")
    # Nothing runs: fall back to the top-ranked build so the error names a real file.
    assert resolve_stockfish_path(str(tmp_path), probe=lambda exe: False).endswith("avx512.exe")
