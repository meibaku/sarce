"""'Why this move?': Brilliant checks, badge reasons, playable lines and the engine fallback."""

import chess

from app.services.explain import ExplainService, badge_reason, brilliant_checks, steps

# White's bishop on c4 can take on f7 (Bxf7+ gives a piece for a pawn and the king's shelter).
FEN = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"


def test_brilliant_checks_report_each_rule_with_numbers():
    # Ng5 drops the knight onto a square the h6 pawn attacks: a 3-point offer.
    offer = chess.Board("rnbqkbnr/ppppppp1/7p/8/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3")
    checks = {c["rule"]: c for c in brilliant_checks(offer, chess.Move.from_uci("f3g5"), 0.4, 0.3, 0.03, 1200)}
    assert checks["A real sacrifice"]["passed"] and "offered 3 points" in checks["A real sacrifice"]["detail"]
    # Bxf7+ wins a pawn back, so it nets only 2 points: below the 3-point minimum.
    board = chess.Board(FEN)
    assert not brilliant_checks(board, chess.Move.from_uci("c4f7"), 0.4, 0.3, 0.03, 1200)[0]["passed"]
    assert checks["It holds up"]["passed"] and "0.01 expected points" in checks["It holds up"]["detail"]
    assert checks["Hard to find"]["passed"] and "3% of 1200-rated" in checks["Hard to find"]["detail"]

    quiet = {c["rule"]: c for c in brilliant_checks(board, chess.Move.from_uci("d2d3"), 4.2, 3.0, 0.6, 1200)}
    assert not quiet["A real sacrifice"]["passed"]
    assert not quiet["It holds up"]["passed"] and "0.07 expected points" in quiet["It holds up"]["detail"]
    assert not quiet["Not already decided"]["passed"]
    assert not quiet["Hard to find"]["passed"]


def test_missing_data_is_said_plainly():
    board = chess.Board(FEN)
    checks = {c["rule"]: c for c in brilliant_checks(board, chess.Move.from_uci("d2d3"), None, None, None, 800)}
    assert not checks["It holds up"]["passed"] and "no engine evaluation" in checks["It holds up"]["detail"]
    assert "No human-model estimate" in checks["Hard to find"]["detail"]


def test_badge_reasons_use_style_copy():
    assert badge_reason(None, {}, {"verdict": "missed"}, False, None).startswith("Didn't hold")
    assert badge_reason(None, {"verdict": "cheap_chaos"}, {}, False, 1.4).endswith("(about 1.4 pawns).")
    assert badge_reason(None, {}, {}, True, None).startswith("Brilliant")
    for text in (badge_reason(None, {}, {}, False, None), badge_reason(None, {"verdict": "real_chaos"}, {}, False, None)):
        assert not any(w in text.lower() for w in ("blunder", "mistake", "inaccuracy"))


def test_steps_follow_a_line_and_stop_at_an_illegal_move():
    out = steps(chess.Board(), ["e2e4", "e7e5", "e1e8"])
    assert [s["san"] for s in out] == ["e4", "e5"]
    assert out[-1]["fen"].startswith("rnbqkbnr/pppp1ppp/8/4p3/4P3/")


class FakeTable:
    def __init__(self, rows):
        self.rows = rows

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def execute(self):
        from types import SimpleNamespace

        return SimpleNamespace(data=self.rows)


def fake_db(monkeypatch, move_row):
    from types import SimpleNamespace

    from app.services import explain

    pgn = '[Event "?"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Bxf7+ *\n'
    tables = {
        "games": [{"pgn": pgn, "user_color": "white", "opponent_rating": 1200}],
        "game_moves": [move_row],
        "move_lens_scores": [],
        "human_probs": [{"probs": {"c4f7": 0.05}}],
        "brilliant_reports": [],
        "move_annotations": [],
    }
    monkeypatch.setattr(explain, "get_supabase", lambda: SimpleNamespace(table=lambda t: FakeTable(tables[t])))


ROW = {"ply": 6, "san": "Bxf7+", "uci": "c4f7", "quality": "best", "cp_loss": 0, "eval_before": 0.3, "eval_after": 0.2, "is_brilliant": True, "signals": ["sacrifice"], "best_uci": "c4f7", "best_san": "Bxf7+", "pv": [{"uci": "c4f7", "eval": 0.3}, {"uci": "d2d3", "eval": 0.1}]}


def test_why_with_engine_lines(monkeypatch):
    fake_db(monkeypatch, ROW)

    class Engine:
        def pv_lines(self, board, multipv=3):
            return [{"uci": [m.uci() for m in list(board.legal_moves)[:2]], "cp": 30, "mate": None}][:multipv]

    out = ExplainService(Engine()).why("g", 6)
    assert out["label"] == "4. Bxf7+" and out["isBrilliant"] and out["badge"].startswith("Brilliant")
    assert out["lines"][0]["title"] == "What you played" and out["lines"][0]["steps"][0]["san"] == "Bxf7+"
    assert {c["rule"] for c in out["brilliant"]} >= {"A real sacrifice", "Hard to find"}
    assert out["playedUci"] == "c4f7" and out["bestMove"] == "Bxf7+"
    assert out["playedEp"] is not None and out["bestEp"] is not None
    assert out["minimumEp"] == round(out["bestEp"] - 0.03, 3)
    assert out["privateNote"] == ""


def test_why_falls_back_to_stored_candidates_without_an_engine(monkeypatch):
    fake_db(monkeypatch, {**ROW, "is_brilliant": False})
    out = ExplainService(None).why("g", 6)
    titles = [ln["title"] for ln in out["lines"]]
    assert titles[:3] == ["What you played", "The engine's first choice", "Alternative 1"]
    assert all(ln["steps"] for ln in out["lines"])


def test_real_offer_rejects_a_defended_piece_only_an_equal_can_take():
    from app.services.brilliant import is_brilliant_move, real_offer

    # 2...Nf6 in the Scandinavian-style position: the knight can be "landed on" but isn't really offered.
    board = chess.Board("rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
    move = chess.Move.from_uci("g8f6")
    assert real_offer(board, move) == 0
    assert not is_brilliant_move(board, move, -0.1, -0.1, -0.1)
    # A knight dropped where a pawn takes it is a genuine 3-point offer.
    offer = chess.Board("rnbqkbnr/ppppppp1/7p/8/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3")
    assert real_offer(offer, chess.Move.from_uci("f3g5")) == 3
