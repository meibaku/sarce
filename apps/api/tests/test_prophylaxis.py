"""Prophylaxis (app/lenses/prophylaxis.py, app/services/threats.py): stopping the opponent's idea first."""

import chess

from app.lenses.base import PlyContext, PositionData
from app.lenses.prophylaxis import ProphylaxisLens
from app.services.position_evals import fen_key
from app.services.threats import null_move_threat

# 1.e4 e5 2.Nf3 Nc6 3.Bc4 Qh4: White to move, and if White passed, ...Qxf2+ would be the threat.
BOARD = chess.Board()
for san in ["e4", "e5", "Nf3", "Nc6", "Bc4", "Qh4"]:
    BOARD.push_san(san)


class FakeEngine:
    def __init__(self, move="h4f2", cp=900):
        self.move, self.cp, self.seen = move, cp, []

    def analyse(self, board, nodes, multipv):
        self.seen.append(board.turn)
        return [{"move_uci": self.move, "cp": self.cp, "mate": None, "ep": 0.9}]


def test_null_move_threat_asks_for_the_other_side():
    engine = FakeEngine()
    threat = null_move_threat(BOARD, engine)
    assert threat == {"threat_uci": "h4f2", "threat_cp": 900}
    assert engine.seen == [chess.BLACK]  # it searched as if White had passed
    check = chess.Board("4k3/8/8/8/8/8/4q3/4K3 w - - 0 1")
    assert null_move_threat(check, FakeEngine()) is None  # never in check


def ctx(uci, edge, reply_cp, threat_cp=900, reply_move="d8e7", reply=None):
    faced = PositionData(
        lines=[{"move_uci": "d1e2", "cp": edge, "mate": None, "ep": 0.5}], safe_set_complete=True,
        key=fen_key(BOARD), threat={"threat_uci": "h4f2", "threat_cp": threat_cp},
    )
    left = PositionData(lines=[{"move_uci": reply_move, "cp": reply_cp, "mate": None, "ep": 0.5}], safe_set_complete=True)
    return PlyContext(ply=6, uci=uci, faced=faced, left=left, reply_uci=reply)


def test_stopped_by_a_quiet_move_that_keeps_the_position():
    r = ProphylaxisLens().score(ctx("d1e2", 30, -30))
    assert r.verdict == "stopped" and r.details["threat"] == "Qxf2+" and r.details["quiet"] is True


def test_met_by_force_is_not_prophylaxis():
    # Bxf7+ keeps the position too, but by force (a capture with check), not by taking the idea away.
    r = ProphylaxisLens().score(ctx("c4f7", 30, -30))
    assert r.verdict == "met" and r.details["quiet"] is False


def test_let_through_when_the_threat_comes():
    r = ProphylaxisLens().score(ctx("a2a3", 30, 400, reply_move="h4f2"))
    assert r.verdict == "let_through" and r.details["cost_cp"] == 430


def test_no_verdict_without_a_real_threat():
    assert ProphylaxisLens().score(ctx("d1e2", 30, -30, threat_cp=60)) is None
