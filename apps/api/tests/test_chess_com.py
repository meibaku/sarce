from app.services import chess_com
from app.services.chess_com import ChessComClient, normalize_chess_com_username


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_normalize_chess_com_username():
    assert normalize_chess_com_username("  HIKARU  ") == "hikaru"


async def test_fetch_recent_archives_uses_canonical_username(monkeypatch):
    calls = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            calls["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, headers):
            calls["url"] = url
            calls["headers"] = headers
            return FakeResponse(
                {
                    "archives": [
                        "https://api.chess.com/pub/player/hikaru/games/2026/05",
                        "https://api.chess.com/pub/player/hikaru/games/2026/06",
                    ]
                }
            )

    monkeypatch.setattr(chess_com.httpx, "AsyncClient", FakeAsyncClient)

    archives = await ChessComClient().fetch_recent_archives("HIKARU", limit=1)

    assert calls["url"].endswith("/player/hikaru/games/archives")
    assert calls["client_kwargs"]["follow_redirects"] is True
    assert calls["headers"]["User-Agent"] == "Sarce/0.1"
    assert archives == ["https://api.chess.com/pub/player/hikaru/games/2026/06"]
