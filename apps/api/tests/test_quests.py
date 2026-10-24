"""Weekly quests (app/services/quests.py, plan 3.6)."""

from unittest.mock import patch

from app.services import quests as q
from app.services.recap import quest_line

REFS = {"Tal": {"axes": {"Chaos created": 30, "Sacrifices per 1,000 moves": 5}}, "Morphy": {"axes": {"Chaos created": 22, "Sacrifices per 1,000 moves": 16}}}


@patch("app.services.quests.references", return_value=REFS)
def test_reference_is_the_player_furthest_above_you(_refs):
    ref = q.reference_for("Chaos", 0.18)
    assert ref["player"] == "Tal" and ref["theirs"] == 30 and ref["yours"] == 18 and "provisional" in ref["label"]
    assert q.reference_for("Chaos", 0.5) is None  # nobody above you
    assert q.reference_for("Grip", 0.8) is None  # no reference axis for Grip yet


def test_quest_line_never_says_failed():
    quest = {"trait": "Sacrifice", "reference": {"label": "Morphy (provisional)"}, "drills": [{}, {}, {}], "done": 2, "verdict": "next week"}
    assert quest_line(quest) == "Quest · Sacrifice, like Morphy (provisional): 2 of 3 drills · next week"
    assert quest_line({**quest, "reference": None, "drills": []}) == "Quest · Sacrifice: no drills from your games yet · next week"
    assert quest_line(None) is None


def test_board_before_and_drills_are_first_in_train():
    pgn = '[Event "?"]\n\n1. e4 e5 2. Nf3 *'
    assert q.board_before(pgn, 2).fen().startswith("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w")
    assert q.board_before(pgn, 9) is None
