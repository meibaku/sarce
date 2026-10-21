"""One search per position: game_lines feeding the classifier, and parallel analyze_pending."""

import asyncio

import chess

from app.services.move_classifier import MoveClassifier, line_pawns
from app.services.position_evals import game_lines


class FakeEngine:
    """Every position: two lines, the first legal move at +0.30 for the side to move."""

    engine_version = "fake"

    def __init__(self, cp: int = 30):
        self.calls: list[int] = []
        self.cp = cp

    def analyse(self, board, nodes, multipv):
        self.calls.append(nodes)
        legal = list(board.legal_moves)[:2]
        return [{"move_uci": m.uci(), "cp": self.cp - 10 * i, "mate": None, "wdl": None, "ep": 0.55 - 0.01 * i} for i, m in enumerate(legal)]


class DictStore:
    def __init__(self):
        self.rows = {}

    def get(self, key, nodes):
        return self.rows.get((key, nodes))

    def put(self, row):
        self.rows[(row["fen_key"], row["nodes"])] = row


def _moves(*sans):
    board, out = chess.Board(), []
    for san in sans:
        move = board.parse_san(san)
        out.append(move)
        board.push(move)
    return out


def test_line_pawns_matches_score_to_pawns():
    assert line_pawns({"cp": 30, "mate": None}) == 0.3
    assert line_pawns({"cp": None, "mate": 2}) == 99.98
    assert line_pawns({"cp": None, "mate": -3}) == -99.97


def test_game_lines_covers_every_position_and_caches_live_ones():
    moves = _moves("e4", "e5", "Nf3")
    store = DictStore()
    lines = game_lines(chess.Board(), moves, FakeEngine(), store)
    assert len(lines) == 4 and all(lines)
    assert len(store.rows) == 4


def test_decided_positions_are_searched_but_not_cached():
    from app.config import settings

    moves = _moves("e4", "e5", "Nf3")
    engine, store = FakeEngine(cp=2000), DictStore()  # +20 pawns: every position after the first is decided
    game_lines(chess.Board(), moves, engine, store)
    assert set(engine.calls) == {settings.analysis_nodes}
    assert len(store.rows) == 1  # only the start position, which nothing precedes


def test_classifier_reads_shared_lines_without_an_engine():
    moves = _moves("e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6", "Qxf7#")
    lines = game_lines(chess.Board(), moves, FakeEngine(), DictStore())
    out = MoveClassifier().classify_game(chess.Board(), moves, "white", lines=lines)
    assert [m["ply"] for m in out] == [0, 2, 4, 6]
    assert out[-1]["eval_after"] == 100.0  # mate delivered
    assert out[0]["eval_before"] == 0.3 and out[0]["eval_after"] == -0.3


def test_analyze_pending_runs_games_in_parallel(monkeypatch):
    from types import SimpleNamespace

    from app.services import analysis as analysis_module

    rows = [{"id": str(i)} for i in range(6)]

    class Q:
        def __getattr__(self, _name):
            return lambda *a, **k: self

        def execute(self):
            return SimpleNamespace(data=rows)

    monkeypatch.setattr(analysis_module, "get_supabase", lambda: SimpleNamespace(table=lambda _t: Q()))
    monkeypatch.setattr(analysis_module.settings, "analysis_workers", 3)
    service = analysis_module.AnalysisService.__new__(analysis_module.AnalysisService)
    running = peak = 0

    async def fake(game_id):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        if game_id == "2":
            raise RuntimeError("bad pgn")
        return {"gameId": game_id}

    service.analyze_game = fake
    out = asyncio.run(service.analyze_pending(limit=6))
    assert peak == 3 and len(out) == 5
