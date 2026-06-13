import httpx

from app.config import settings


class ChessComClient:
    def __init__(self) -> None:
        self.base = settings.chess_com_api_base.rstrip("/")

    async def fetch_recent_archives(self, username: str, limit: int = 3) -> list[str]:
        url = f"{self.base}/player/{username}/games/archives"
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(url, headers={"User-Agent": "Sarce/0.1"})
            res.raise_for_status()
            data = res.json()

        archives = data.get("archives", [])
        return archives[-limit:]

    async def fetch_games_from_archive(self, archive_url: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.get(archive_url, headers={"User-Agent": "Sarce/0.1"})
            res.raise_for_status()
            data = res.json()

        return data.get("games", [])
