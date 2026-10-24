"""Swindle lens (app/lenses/swindle.py): fighting back once clearly losing."""

from app.lenses.base import PlyContext, PositionData
from app.lenses.swindle import SwindleLens
from app.services.lens_service import increment_ms, spent_on
from app.services.ep import cp_to_ep


def faced(cp):
    return PositionData(lines=[{"move_uci": "a", "cp": cp, "mate": None, "ep": cp_to_ep(cp)}], safe_set_complete=True)


def left(probs, complete=True):
    # Opponent to move: one safe reply (s1); everything else loses a lot.
    lines = [{"move_uci": "s1", "cp": 300, "mate": None, "ep": 0.9}, {"move_uci": "x1", "cp": -100, "mate": None, "ep": 0.3}, {"move_uci": "x2", "cp": -150, "mate": None, "ep": 0.25}]
    return PositionData(lines=lines, safe_set_complete=complete, probs_by_elo={800: probs})


def ctx(edge, probs, reply=None, complete=True):
    return PlyContext(ply=30, uci="m", faced=faced(edge), left=left(probs, complete), opponent_elo=800, reply_uci=reply)


TRAP = {"s1": 0.2, "x1": 0.5, "x2": 0.3}  # an 800 player usually misses the one safe reply
EASY = {"s1": 0.95, "x1": 0.03, "x2": 0.02}


def test_only_moves_made_while_clearly_losing():
    assert SwindleLens().score(ctx(-50, TRAP)) is None


def test_drifted_when_no_real_problem_is_set():
    assert SwindleLens().score(ctx(-400, EASY)).verdict == "drifted"


def test_sprung_when_the_opponent_misses_every_safe_reply():
    r = SwindleLens().score(ctx(-400, TRAP, reply="x1"))
    assert r.verdict == "sprung" and r.details["fell"] is True and r.details["p_fail"] == 0.8


def test_set_when_they_found_it_or_it_is_unknown():
    assert SwindleLens().score(ctx(-400, TRAP, reply="s1")).verdict == "set"
    assert SwindleLens().score(ctx(-400, TRAP, reply="x1", complete=False)).details["fell"] is None


def test_time_spent_from_clocks():
    clocks = [59_000, 58_000, 55_000, 57_500]  # ply 2: 59.0s -> 55.0s; ply 3: 58.0s -> 57.5s
    assert spent_on(clocks, 2, 60_000) == (59_000, 4_000)
    assert spent_on(clocks, 0, 60_000) == (60_000, 1_000)
    assert spent_on(clocks, 3, 60_000, inc_ms=1_000) == (58_000, 1_500)
    assert spent_on([], 4, 60_000) == (None, None)
    assert increment_ms("180+2") == 2_000 and increment_ms("60") == 0


def test_clock_lens_verdicts():
    from app.lenses.clock import ClockLens

    def c(faced_cps, reply_cp, spent):
        f = PositionData(lines=[{"move_uci": f"m{i}", "cp": cp, "mate": None, "ep": cp_to_ep(cp)} for i, cp in enumerate(faced_cps)], safe_set_complete=True)
        l = PositionData(lines=[{"move_uci": "r", "cp": reply_cp, "mate": None, "ep": cp_to_ep(reply_cp)}], safe_set_complete=True)
        return ClockLens().score(PlyContext(ply=10, uci="m0", faced=f, left=l, spent_ms=spent, initial_ms=60_000))

    assert c([200, 50], -200, 4_000).verdict == "found"      # one clear move, found
    assert c([200, 50], 50, 1_000).verdict == "rushed"       # one clear move, played in a second, missed
    assert c([200, 50], 50, 4_000).verdict == "missed"       # thought about it, still missed: not a time slip
    assert c([30, 20], -30, 1_000).verdict == "quick"
    assert c([30, 20], -30, 6_000).verdict == "lingered"
    assert c([30, 20], -30, 3_000).verdict == "steady"
    assert ClockLens().score(PlyContext(ply=10, uci="m0")) is None
