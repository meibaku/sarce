"""Site rating → human-model Elo (app/services/rating_map.py, review F1)."""

from app.services.brilliant_find_rate import mover_rung
from app.services.rating_map import opponent_model_elo, speed, to_model_elo


def test_speed_classes():
    assert speed("chess_com", "60") == "bullet" and speed("chess_com", "180+2") == "blitz"
    assert speed("chess_com", "600") == "rapid" and speed("chess_com", "1/86400") == "rapid"
    assert speed("lichess", "480") == "rapid" and speed("lichess", "1800") == "classical" and speed(None, None) == "rapid"


def test_chess_com_matches_the_survey_rows():
    # ChessGoals: Chess.com blitz 1000 = Chess.com rapid 1255 = bullet 920 → Lichess rapid 1615 / bullet 1375.
    assert to_model_elo("chess_com", "600", 1255) == 1615
    assert to_model_elo("chess_com", "60", 920) == 1375
    assert to_model_elo("chess_com", "180", 1000) == 1425


def test_below_the_survey_extends_and_clamps():
    assert 1100 < to_model_elo("chess_com", "600", 663) < 1250
    assert to_model_elo("chess_com", "60", 50) >= 400


def test_other_sources_pass_through():
    assert to_model_elo("lichess", "180", 1500) == 1500 and to_model_elo("sarce_bot", "180", 1200) == 1200
    assert to_model_elo("chess_com", "600", None) is None
    assert opponent_model_elo({"source": "chess_com", "time_control": "600", "opponent_rating": 1255}) == 1615


def test_find_rate_rung_is_the_movers_own_rating():
    game = {"source": "chess_com", "time_control": "600", "opponent_rating": 1255, "user_rating": 663}
    assert mover_rung(game) == 1200  # your ~1,170 on the model's scale, not the opponent's 1,615
    assert mover_rung({**game, "user_rating": None}) == 1600
    assert mover_rung({}) == 1600
