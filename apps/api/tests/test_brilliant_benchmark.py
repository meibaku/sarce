"""Brilliant under rule v3 for references and you (app/services/brilliant_benchmark.py, review F6)."""

import chess

from app.services import brilliant_benchmark as bb
from app.services.brilliant import CLAUSES, best_eval_from_row, brilliant_clauses, is_brilliant_move


def board_after(sans):
    b = chess.Board()
    for san in sans:
        b.push_san(san)
    return b


def test_clauses_match_is_brilliant_and_name_the_failure():
    # 1.e4 c6 2.Nc3 e6 3.Nb5: a real offer (the c6 pawn takes the knight).
    b, move = board_after(["e4", "c6", "Nc3", "e6"]), chess.Move.from_uci("c3b5")
    sound = brilliant_clauses(b, move, 0.2, 0.1, 0.2)
    assert sound["real_sacrifice"] and sound["sound"] and is_brilliant_move(b, move, 0.2, 0.1, 0.2)
    unsound = brilliant_clauses(b, move, 0.2, -2.5, 0.2)
    assert unsound["sound"] is False and bb.first_failure(unsound) == "sound"
    assert not is_brilliant_move(b, move, 0.2, -2.5, 0.2)
    winning = brilliant_clauses(b, move, 5.0, 4.9, 5.0)
    assert bb.first_failure(winning) == "not_already_winning"
    assert list(sound) == list(CLAUSES)


def test_hard_to_find_uses_the_human_model():
    b, move = board_after(["e4", "c6", "Nc3", "e6"]), chess.Move.from_uci("c3b5")
    assert brilliant_clauses(b, move, 0.2, 0.1, 0.2, {"c3b5": 0.6})["hard_to_find"] is False
    assert brilliant_clauses(b, move, 0.2, 0.1, 0.2, {"c3b5": 0.05})["hard_to_find"] is True
    assert brilliant_clauses(b, move, 0.2, 0.1, 0.2)["hard_to_find"] is None


def test_games_without_the_player_are_skipped():
    pgn = '[White "Someone Else"]\n[Black "Another"]\n\n1. e4 e5 *'
    assert bb.benchmark_game(pgn, "Mikhail Tal", engine=None, model=None) is None


def test_bootstrap_resamples_whole_games():
    # 50 games of 40 moves; one Brilliant in every fifth game: pooled 0.5%.
    per_game = [(1 if i % 5 == 0 else 0, 40) for i in range(50)]
    s = bb.summarize([{"brilliant": b, "moves": n, "candidates": 0, "stopped_by": {}} for b, n in per_game])
    assert s["brilliantPct"] == 0.5 and s["interval"][0] < 0.5 < s["interval"][1]
    assert bb.bootstrap_interval([]) is None


def test_outcome_separates_unjudged_from_brilliant():
    judged = {"real_sacrifice": True, "sound": True, "not_lost": True, "not_already_winning": True, "not_forced": True}
    assert bb.outcome({**judged, "sound": None, "not_lost": None, "not_already_winning": None, "hard_to_find": None}) == "no_evals"
    assert bb.outcome({**judged, "hard_to_find": None}) == "brilliant"
    assert bb.outcome({**judged, "hard_to_find": False}) == "hard_to_find"


def test_even_sample_spans_the_whole_corpus():
    corpus = [str(i) for i in range(399)]
    picked = bb.even_sample(corpus, 200)
    assert len(picked) == 200 and picked[0] == "0" and int(picked[-1]) > 390
    assert bb.even_sample(corpus[:5], 200) == corpus[:5]


def test_best_eval_from_row_is_the_soundness_comparator():
    # eval_after + cp_loss is exactly what classification compared; a clamped 0 means the move scored at least as
    # well as the best line, which passes the one-sided v4 test either way.
    assert best_eval_from_row({"eval_after": 1.0, "cp_loss": 50}) == 1.5
    assert best_eval_from_row({"eval_after": 1.0, "cp_loss": 0}) == 1.0
    assert best_eval_from_row({"eval_after": None, "cp_loss": 20}) is None


def test_reference_rung_uses_the_players_own_elo():
    import chess.pgn

    game = chess.pgn.Game()
    game.headers.update({"White": "Tal, Mikhail", "Black": "X", "WhiteElo": "2630", "BlackElo": "2550"})
    assert bb.reference_rung(game, "white") == 2600
    del game.headers["WhiteElo"]
    assert bb.reference_rung(game, "white") == 2600  # the opponent's 2550, rounded
    del game.headers["BlackElo"]
    assert bb.reference_rung(game, "white") == 2400
