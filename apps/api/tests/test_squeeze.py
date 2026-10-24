"""Squeeze lens (app/lenses/squeeze.py): converting an advantage by taking the opponent's options away."""

from app.lenses.base import PlyContext, PositionData
from app.lenses.squeeze import SqueezeLens, line_cp, line_points, room
from app.services.ep import cp_to_ep


def pos(*cps, complete=True):
    return PositionData(lines=[{"move_uci": f"m{i}", "cp": cp, "mate": None, "ep": cp_to_ep(cp)} for i, cp in enumerate(cps)], safe_set_complete=complete)


def ctx(faced_best, left_cps, complete=True):
    return PlyContext(ply=20, uci="m0", faced=pos(faced_best, faced_best - 80), left=pos(*left_cps, complete=complete))


def test_line_cp_and_mates():
    assert line_cp({"cp": 150, "mate": None}) == 150
    assert line_cp({"cp": None, "mate": 3}) > 9000 and line_cp({"cp": None, "mate": -2}) < -9000


def test_room_counts_holding_replies():
    assert room([{"cp": -300}, {"cp": -320}, {"cp": -500}], complete=True) == (2, True)
    # Every stored line holds and the search was cut short: a lower bound only.
    assert room([{"cp": -300}, {"cp": -310}], complete=False) == (2, False)


def test_only_scores_moves_made_while_clearly_winning():
    assert SqueezeLens().score(ctx(120, [-120, -130])) is None


def test_squeezed_when_the_edge_holds_and_one_reply_is_left():
    r = SqueezeLens().score(ctx(320, [-320, -600, -700]))
    assert r.verdict == "squeezed" and r.score == 1.0 and r.details["replies_that_hold"] == 1


def test_kept_when_the_opponent_still_has_room():
    r = SqueezeLens().score(ctx(320, [-310, -320, -330, -340, -350]))
    assert r.verdict == "kept" and 0 < r.score < 1


def test_gave_air_when_the_edge_drops_by_more_than_a_pawn():
    r = SqueezeLens().score(ctx(350, [-200, -210]))
    assert r.verdict == "gave_air" and r.score == 0.0 and r.details["cost_cp"] == 150


def test_giving_back_a_pawn_from_a_big_edge_is_not_air():
    # +8 to +6.5 is still winning comfortably: in expected points it costs almost nothing (review F8).
    r = SqueezeLens().score(ctx(800, [-650, -660]))
    assert r.verdict != "gave_air" and r.details["cost_ep"] < 0.05


def test_stored_ep_wins_over_the_centipawn_score():
    # Stockfish's WDL can disagree with the logistic curve: the lens must read the stored EP (review F8).
    # Same +4 → +2.5 scores; the stored EP says the edge barely moved (0.95 → 0.93), so it isn't "air".
    faced = PositionData(lines=[{"move_uci": "m0", "cp": 400, "mate": None, "ep": 0.95}, {"move_uci": "m1", "cp": 320, "mate": None, "ep": 0.94}], safe_set_complete=True)
    left = PositionData(lines=[{"move_uci": "r0", "cp": -250, "mate": None, "ep": 0.07}], safe_set_complete=True)
    r = SqueezeLens().score(PlyContext(ply=20, uci="m0", faced=faced, left=left))
    assert r.verdict != "gave_air" and r.details["cost_ep"] == 0.02
    # From centipawns alone the same move would cost about 0.1 EP: air.
    assert line_points({"cp": 400, "mate": None}) - line_points({"cp": 250, "mate": None}) > 0.09
