"""Shared links: what a snapshot may contain, who can make one, revocation, and multi-user sync owners."""

from types import SimpleNamespace

import pytest

from app.services import sharing, sync
from app.services.sharing import ShareService, sacrifice_snapshot, summary_snapshot

SUMMARY = {
    "opponent": "real_person_42",
    "result": "win",
    "userColor": "white",
    "timeControl": "10+0",
    "headline": "Two real problems set.",
    "outcome": {"kicker": "Won", "text": "Won on move 21."},
    "brilliant": {"pct": 4.8, "count": 1, "of": 21, "rolling": 1.1, "goalLo": 6, "goalHi": 10},
    "moments": [{"ply": 20, "san": "Bxh7+", "glyph": "!!", "line": "The sacrifice held", "clock": "0:41"}],
    "questions": [{"kind": "intent", "ply": 20}],
    "styleRead": 61,
}


def test_summary_snapshot_names_no_one_and_keeps_no_private_answers():
    snap = summary_snapshot(SUMMARY)
    text = repr(snap)
    assert "real_person_42" not in text
    assert "questions" not in snap and "rolling" not in snap["brilliant"]
    assert snap["moments"] == [{"label": "11. Bxh7+", "glyph": "!!", "line": "The sacrifice held"}]


def test_sacrifice_snapshot_has_no_opponent_or_note():
    row = {"label": "11. Bxh7+", "glyph": "!!", "type": "Piece", "material": 3, "held": True, "opponent": "real_person_42", "note": "secret plan", "opening": "C50", "playedAt": "2026-10-18T10:00:00Z"}
    snap = sacrifice_snapshot(row, "fen")
    assert "real_person_42" not in repr(snap) and "secret plan" not in repr(snap)
    assert snap["playedAt"] == "2026-10-18"


class FakeTable:
    def __init__(self, rows):
        self.rows = rows

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def execute(self):
        return SimpleNamespace(data=self.rows)


def test_only_the_owner_can_share_a_game(monkeypatch):
    monkeypatch.setattr(sharing, "get_supabase", lambda: SimpleNamespace(table=lambda t: FakeTable([{"id": "g", "user_id": "someone-else", "pgn": ""}])))
    with pytest.raises(LookupError):
        ShareService().create("me", "summary", "g", None)
    with pytest.raises(ValueError):
        ShareService().create("me", "poster", "g", None)


def test_revoked_or_unknown_tokens_answer_nothing(monkeypatch):
    monkeypatch.setattr(sharing, "get_supabase", lambda: SimpleNamespace(table=lambda t: FakeTable([{"kind": "summary", "snapshot": {"kind": "summary"}, "created_at": "x", "revoked_at": "2026-10-21"}])))
    assert ShareService().public("tok") is None
    monkeypatch.setattr(sharing, "get_supabase", lambda: SimpleNamespace(table=lambda t: FakeTable([])))
    assert ShareService().public("tok") is None
    monkeypatch.setattr(sharing, "get_supabase", lambda: SimpleNamespace(table=lambda t: FakeTable([{"kind": "summary", "snapshot": {"kind": "summary", "headline": "h"}, "created_at": "x", "revoked_at": None}])))
    assert ShareService().public("tok") == {"kind": "summary", "headline": "h", "sharedAt": "x"}


def test_public_route_needs_no_sign_in(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import app
    from app.routers import shares

    monkeypatch.setattr(settings, "auth_required", True)
    monkeypatch.setattr(shares.service, "public", lambda token: {"kind": "summary"} if token == "good" else None)
    client = TestClient(app)
    assert client.get("/public/shares/good").status_code == 200
    assert client.get("/public/shares/bad").status_code == 404
    assert client.post("/shares", json={"kind": "summary", "gameId": "g"}).status_code == 401  # making links does


def test_sync_serves_every_user_with_a_username(monkeypatch):
    rows = [
        {"id": "a", "settings": {"chessComUsername": "alice"}},
        {"id": "b", "settings": {"lichessUsername": "bob"}},
        {"id": "c", "settings": {}},
    ]
    monkeypatch.setattr(sync, "get_supabase", lambda: SimpleNamespace(table=lambda t: FakeTable(rows)))
    assert sync.owners_to_sync("local") == ["a", "b", "local"]
    assert sync.owners_to_sync("a") == ["a", "b"]
