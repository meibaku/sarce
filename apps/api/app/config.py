from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_STOCKFISH_DIR = Path(r"C:\Users\user\Documents\stockfish")


def resolve_stockfish_path(path: str) -> str:
    """Accept a folder or full path; find stockfish.exe on Windows when given a directory."""
    candidate = Path(path)
    if candidate.is_file():
        return str(candidate)

    if candidate.is_dir():
        for name in ("stockfish.exe", "stockfish"):
            exe = candidate / name
            if exe.is_file():
                return str(exe)
        release_builds = sorted(candidate.glob("stockfish*.exe"))
        if release_builds:
            return str(release_builds[0])

    return path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    stockfish_path: str = str(DEFAULT_STOCKFISH_DIR)
    chess_com_api_base: str = "https://api.chess.com/pub"
    analysis_depth: int = 18
    cors_origins: list[str] = ["http://localhost:3000"]

    # Local-first dev: fixed user UUID from supabase/seed.sql
    local_user_id: str = "00000000-0000-4000-8000-000000000001"

    # Brilliant detection thresholds (tunable)
    brilliant_eval_margin: float = 0.3
    brilliant_winning_margin: float = 3.0

    @property
    def stockfish_executable(self) -> str:
        return resolve_stockfish_path(self.stockfish_path)


settings = Settings()
