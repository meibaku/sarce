import pytest

from app.services.train import check_move

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_matching_answer_ignores_check_marks():
    out = check_move(START, "e2e4", "e4+", False)
    assert out["matched"] and out["san"] == "e4" and out["line"] == "That's the move."


def test_sound_alternative_in_a_sacrifice_drill_is_not_the_sacrifice():
    out = check_move(START, "d2d4", "e4", True, loss=lambda b, m: 0.01)
    assert not out["matched"] and out["sound"] is True and "not the sacrifice" in out["line"]


def test_unsound_move_and_engine_failure():
    assert check_move(START, "g2g4", "e4", False, loss=lambda b, m: 0.2)["sound"] is False

    def broken(b, m):
        raise RuntimeError("no engine")

    assert check_move(START, "g2g4", "e4", False, loss=broken)["sound"] is None


def test_illegal_move_raises():
    with pytest.raises(ValueError):
        check_move(START, "e2e5", "e4", False)


def test_reference_drill_names_the_master_not_the_engine():
    assert check_move(START, "e2e4", "e4", False, reference_player="Tal")["line"] == "That's what Tal played."
    out = check_move(START, "d2d4", "e4", False, loss=lambda b, m: 0.0, reference_player="Shirov")
    assert out["line"] == "That holds too. Shirov played e4."


def test_reference_items_mix_masters(monkeypatch):
    from app.services import reference_axes, train

    library = {
        "Morphy": [{"eco": "C51", "fen": "m1", "san": "Ba4", "year": "1858", "opponent": "Anderssen", "event": ""}],
        "Shirov": [{"eco": "C55", "fen": "s1", "san": "Nxe5", "year": "1996", "opponent": "x", "event": ""}],
        "Tal": [{"eco": "C50", "fen": "t1", "san": "Bxf7+", "year": "1960", "opponent": "y", "event": ""}],
    }
    monkeypatch.setattr(reference_axes, "reference_positions", lambda: library)
    items = train.reference_items(["C50"], seed=0)
    assert {i["source"] for i in items} == {"Morphy in your openings", "Shirov in your openings", "Tal in your openings"}
    assert all(i["title"].startswith("What did ") for i in items)


def test_in_your_openings_prefers_exact_eco_then_family():
    from app.services.reference_axes import in_your_openings

    positions = [{"eco": "C50", "fen": "a"}, {"eco": "C55", "fen": "b"}, {"eco": "B20", "fen": "c"}]
    picks = in_your_openings(positions, ["C54", "B20"], seed=0, count=3)
    # Exact pass: only B20 matches. Family pass: C5x gives "a" (seed 0); B2x has nothing new.
    assert [p["fen"] for p in picks] == ["c", "a"]
