"""Positions from videos: link parsing, transcript windows, AI output checks and the opt-in gate."""

import pytest
from fastapi.testclient import TestClient

from app.services import ai
from app.services.positions import search
from app.services.video import excerpt, start_seconds, youtube_id


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=95s",
        "https://youtu.be/dQw4w9WgXcQ?t=95",
        "youtube.com/shorts/dQw4w9WgXcQ",
        "https://m.youtube.com/embed/dQw4w9WgXcQ",
        "dQw4w9WgXcQ",
    ],
)
def test_youtube_id_from_common_links(url):
    assert youtube_id(url) == "dQw4w9WgXcQ"


def test_non_youtube_links_are_rejected():
    assert youtube_id("https://vimeo.com/123") is None
    assert youtube_id("https://www.youtube.com/watch?v=short") is None


def test_start_seconds_formats():
    assert start_seconds("https://youtu.be/x?t=95") == 95
    assert start_seconds("https://youtu.be/x?t=1m35s") == 95
    assert start_seconds("https://youtube.com/watch?v=x&start=7") == 7
    assert start_seconds("https://youtu.be/x") is None


def test_excerpt_keeps_the_window_around_the_moment():
    snippets = [{"text": f"line {i}", "start": float(i * 10), "duration": 5.0} for i in range(20)]
    out = excerpt(snippets, at_s=100, window_s=20)
    assert out["text"] == "line 8 line 9 line 10 line 11 line 12"
    assert (out["start"], out["end"]) == (80.0, 125.0)
    assert excerpt([], 50)["text"] == ""


def test_checked_fen_builds_a_legal_position_with_honest_castling():
    out = ai.checked_fen({"placement": "r3k2r/8/8/8/8/8/8/4K2R", "side_to_move": "b", "confidence": "high", "notes": "", "flipped": False})
    assert out["fen"] == "r3k2r/8/8/8/8/8/8/4K2R b Kkq - 0 1"


def test_checked_fen_rejects_impossible_readings():
    with pytest.raises(ValueError):
        ai.checked_fen({"placement": "8/8/8/8/8/8/8/8", "side_to_move": "w"})  # no kings
    with pytest.raises(ValueError):
        ai.checked_fen({"placement": "not a board", "side_to_move": "w"})


def test_summarize_trims_ideas(monkeypatch):
    monkeypatch.setattr(ai, "_json_response", lambda content, schema, max_tokens=4000: {"title": "Greek gift", "summary": "Bxh7+ wins.", "ideas": ["Bxh7+", "", "Ng5+", "Qh5", "extra"]})
    out = ai.summarize_excerpt("he plays bishop takes h7 check")
    assert out["ideas"] == ["Bxh7+", "Ng5+", "Qh5"]
    with pytest.raises(ValueError):
        ai.summarize_excerpt("   ")


def test_search_matches_every_word_across_fields():
    rows = [
        {"title": "Greek gift", "note": "", "excerpt": "bishop takes h7", "ai_summary": ""},
        {"title": "Endgame", "note": "rook behind the pawn", "excerpt": "", "ai_summary": ""},
    ]
    assert [r["title"] for r in search(rows, "bishop GREEK")] == ["Greek gift"]
    assert search(rows, "rook queen") == []


def test_ai_routes_need_credentials_and_the_opt_in(monkeypatch):
    from app.main import app
    from app.routers import videos

    client = TestClient(app)
    monkeypatch.setattr(videos.ai, "credentials_present", lambda: False)
    r = client.post("/videos/summary", json={"excerpt": "x"})
    assert r.status_code == 403 and "credentials" in r.json()["detail"]

    monkeypatch.setattr(videos.ai, "credentials_present", lambda: True)
    monkeypatch.setattr(videos.SettingsStore, "get", lambda self, owner: {"aiHelp": False})
    r = client.post("/videos/summary", json={"excerpt": "x"})
    assert r.status_code == 403 and "Settings" in r.json()["detail"]

    monkeypatch.setattr(videos.SettingsStore, "get", lambda self, owner: {"aiHelp": True})
    monkeypatch.setattr(videos.ai, "summarize_excerpt", lambda text, fen=None: {"title": "t", "summary": "s", "ideas": []})
    assert client.post("/videos/summary", json={"excerpt": "x"}).json()["title"] == "t"


def test_excerpt_route_rejects_other_sites():
    from app.main import app

    r = TestClient(app).post("/videos/excerpt", json={"url": "https://vimeo.com/1"})
    assert r.status_code == 422


def test_pasted_transcript_with_timestamps_gives_a_window():
    from app.services.video import parse_pasted

    pasted = "0:58\nhere he goes\n1:05\nbishop takes h7 check\n1:12 the Greek gift\n10:00\nmuch later"
    snippets = parse_pasted(pasted)
    assert [s["start"] for s in snippets] == [58.0, 65.0, 72.0, 600.0]
    assert excerpt(snippets, 66, 10)["text"] == "here he goes bishop takes h7 check the Greek gift"
    assert parse_pasted("no stamps at all\njust words") == [{"start": 0.0, "duration": 0.0, "text": "no stamps at all just words"}]


def test_excerpt_route_uses_the_pasted_transcript():
    from app.main import app

    r = TestClient(app).post("/videos/excerpt", json={"url": "https://youtu.be/dQw4w9WgXcQ?t=65", "transcript": "1:05\nbishop takes h7"})
    assert r.status_code == 200 and r.json()["text"] == "bishop takes h7" and r.json()["pasted"] is True


def test_pasted_text_without_timestamps_is_kept_whole():
    from app.main import app

    r = TestClient(app).post("/videos/excerpt", json={"url": "https://youtu.be/dQw4w9WgXcQ?t=600", "transcript": "the Greek gift idea"})
    assert r.json()["text"] == "the Greek gift idea"
