from scripts.pilot_smoke import clone_game, contains_forbidden, pseudonym


def test_nested_experimental_fields_are_rejected():
    assert contains_forbidden({"moments": [{"chaos": None}]}) is True
    assert contains_forbidden({"moments": [{"criteria": ["sound"]}]}) is False


def test_pseudonyms_are_salted_and_repeatable():
    assert pseudonym("user-a", "salt") == pseudonym("user-a", "salt")
    assert pseudonym("user-a", "salt") != pseudonym("user-a", "other")
    assert "user-a" not in pseudonym("user-a", "salt")


def test_cloned_games_get_new_owned_safe_identifiers():
    original = {
        "id": "original", "user_id": "old", "created_at": "yesterday",
        "external_id": "https://chess.com/game/live/1", "pgn": "1. e4 e5 1-0",
    }
    clone = clone_game(original, "new-owner", 2)
    assert clone["id"] != original["id"]
    assert clone["user_id"] == "new-owner"
    assert clone["external_id"].startswith("https://chess.com/game/live/sarce-smoke-2-")
    assert "created_at" not in clone
