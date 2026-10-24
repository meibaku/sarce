"""Brilliant find-rate rule (ADR 0004)."""

from app.services import brilliant, brilliant_find_rate as rule


def test_hard_to_find():
    assert brilliant.hard_to_find({"e1e5": 0.14}, "e1e5") is True
    assert brilliant.hard_to_find({"e1e5": 0.35}, "e1e5") is False
    assert brilliant.hard_to_find({"d1d2": 0.9}, "e1e5") is True  # never played by the model = hidden
    assert brilliant.hard_to_find(None, "e1e5") is None


def test_apply_rule_demotes_only_easy_brilliants_with_data():
    moves = [
        {"ply": 10, "uci": "e1e5", "quality": "brilliant", "is_brilliant": True},
        {"ply": 20, "uci": "c4f7", "quality": "brilliant", "is_brilliant": True},
        {"ply": 30, "uci": "g1h1", "quality": "brilliant", "is_brilliant": True},
        {"ply": 40, "uci": "a2a3", "quality": "good", "is_brilliant": False},
    ]
    probs = {10: {"e1e5": 0.12}, 20: {"c4f7": 0.55}, 30: None, 40: {"a2a3": 0.9}}
    updated, demoted = rule.apply_rule(moves, lambda ply: probs[ply])
    assert demoted == 1
    assert [m["quality"] for m in updated] == ["brilliant", "best", "brilliant", "good"]
    assert updated[1]["is_brilliant"] is False


def test_style_vector_v2_keeps_other_features():
    v = rule.style_vector_v2({"version": 1, "sacrificeRate": 0.1}, {"brilliant": 1, "best": 9}, 10.0)
    assert v["version"] == 5 and v["brilliantRule"] == "v4"
    assert v["sacrificeRate"] == 0.1 and v["brilliantPct"] == 10.0


def test_rung_for():
    assert rule.rung_for(1580) == 1600
    assert rule.rung_for(300) == 800
    assert rule.rung_for(None) == 1600


def test_rejudge_promotes_and_demotes_from_stored_data():
    import chess

    board = chess.Board("rnb1kb1r/pppp1ppp/5n2/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR w KQkq - 0 3")
    sac = chess.Move.from_uci("h5f7")
    row = {"ply": 0, "uci": "h5f7", "best_uci": "h5f7", "cp_loss": 0, "eval_before": 0.3, "eval_after": 0.3,
           "pv": [{"uci": "h5f7", "eval": 0.3}, {"uci": "h5h4", "eval": 0.2}], "quality": "best", "is_brilliant": False}
    updated, changed = rule.rejudge([row], [(board, sac)], lambda ply: {"h5f7": 0.05})
    assert changed == 1 and updated[0]["is_brilliant"] and updated[0]["quality"] == "brilliant"
    # Easy to find at your rating: back to its centipawn quality.
    updated, changed = rule.rejudge([{**row, "is_brilliant": True, "quality": "brilliant"}], [(board, sac)], lambda ply: {"h5f7": 0.6})
    assert changed == 1 and not updated[0]["is_brilliant"] and updated[0]["quality"] == "best"
