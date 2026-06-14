import httpx

from app.config import settings


def normalize_chess_com_username(username: str) -> str:
    """Chess.com public API player URLs are canonicalized to lowercase."""
    return username.strip().lower()


class ChessComClient:
    def __init__(self) -> None:
        self.base = settings.chess_com_api_base.rstrip("/")

    async def fetch_recent_archives(
        self, username: str, limit: int | None = 3
    ) -> list[str]:
        normalized_username = normalize_chess_com_username(username)
        url = f"{self.base}/player/{normalized_username}/games/archives"
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            res = await client.get(url, headers={"User-Agent": "Sarce/0.1"})
            res.raise_for_status()
            data = res.json()

        archives = data.get("archives", [])
        return archives if limit is None else archives[-limit:]

    async def fetch_games_from_archive(self, archive_url: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            res = await client.get(archive_url, headers={"User-Agent": "Sarce/0.1"})
            res.raise_for_status()
            data = res.json()

        return data.get("games", [])
