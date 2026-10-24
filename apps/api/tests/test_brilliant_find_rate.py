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
    assert v["version"] == 4 and v["brilliantRule"] == "find-rate-20@mover+real-offer"
    assert v["sacrificeRate"] == 0.1 and v["brilliantPct"] == 10.0


def test_rung_for():
    assert rule.rung_for(1580) == 1600
    assert rule.rung_for(300) == 800
    assert rule.rung_for(None) == 1600
