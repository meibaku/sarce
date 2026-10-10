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
    lichess_api_base: str = "https://lichess.org/api"
    analysis_depth: int = 18
    cors_origins: list[str] = ["http://localhost:3000"]

    # Durable per-user analysis queue (needs the analysis_jobs migration). Off: BackgroundTasks.
    job_queue_enabled: bool = False
    job_poll_seconds: float = 2.0
    job_stale_minutes: int = 60

    # Local-first dev: fixed user UUID from supabase/seed.sql
    local_user_id: str = "00000000-0000-4000-8000-000000000001"

    # Chaos Lens raw data (docs/CHAOS_PLAN.md, M1). Off until the position_evals
    # migration is applied; when on, every analysed game also gets node-limited
    # MultiPV evaluations for the position after each ply.
    position_evals_enabled: bool = False
    analysis_nodes: int = 1_500_000
    analysis_multipv: int = 4
    analysis_multipv_cap: int = 8
    safe_set_tol: float = 0.05
    ep_decided_low: float = 0.05
    ep_decided_high: float = 0.95
    # Human move model behind services/human_model.py (docs/adr/0002-human-model.md).
    human_model: str = "heuristic"  # or "maia2" (optional install: requirements-maia.txt)
    maia2_model_type: str = "blitz"  # "blitz" or "rapid"
    maia2_cache_dir: str = ".cache/maia2"
    # Intention tagger (M7): engine-free motif tags and idea windows. Off until the
    # intention_tags migration is applied.
    idea_tagger_enabled: bool = False

    # Brilliant detection thresholds (tunable)
    brilliant_eval_margin: float = 0.3
    brilliant_winning_margin: float = 3.0

    @property
    def stockfish_executable(self) -> str:
        return resolve_stockfish_path(self.stockfish_path)


settings = Settings()
