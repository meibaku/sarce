"""Every Chess.com PubAPI request identifies Sarce with a contact User-Agent (their API guidance)."""

import httpx

from app.services import chess_com
from app.services.chess_com import USER_AGENT, ChessComClient


def _capture_requests(monkeypatch) -> list[httpx.Request]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/archives"):
            return httpx.Response(200, json={"archives": ["https://api.chess.com/pub/player/x/games/2026/10"]})
        return httpx.Response(200, json={"games": []})

    real_client = httpx.AsyncClient

    def mock_client(*args, **kwargs):
        return real_client(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(chess_com.httpx, "AsyncClient", mock_client)
    return seen


async def test_archive_list_and_game_downloads_send_contact_user_agent(monkeypatch):
    seen = _capture_requests(monkeypatch)
    client = ChessComClient()

    archives = await client.fetch_recent_archives("X")
    await client.fetch_games_from_archive(archives[0])

    assert len(seen) == 2
    assert all(r.headers["User-Agent"] == USER_AGENT for r in seen)
