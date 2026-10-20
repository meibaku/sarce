from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_STOCKFISH_DIR = Path(r"C:\Users\user\Documents\stockfish")


# Stockfish release builds, fastest first. A folder holding several builds (the user downloaded
# more than one, or a packaged app ships them all) gets the fastest one this CPU can actually run.
BUILD_PREFERENCE = ("vnni512", "avx512icl", "avx512", "avxvnni", "avx2", "bmi2", "sse41-popcnt", "modern", "ssse3", "sse3-popcnt")


def build_rank(name: str) -> int:
    """Position of a build in BUILD_PREFERENCE by its file name; unknown builds go last."""
    lower = name.lower()
    return next((i for i, arch in enumerate(BUILD_PREFERENCE) if arch in lower), len(BUILD_PREFERENCE))


def build_runs(exe: str, timeout: float = 10.0) -> bool:
    """
    True when the build starts and searches on this machine. A build for instructions the CPU
    lacks (avx512 on an older chip) dies with an illegal instruction instead of printing a move.
    """
    import subprocess

    try:
        out = subprocess.run(
            [exe],
            input="uci\nisready\nposition startpos\ngo nodes 20000\n",
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return "bestmove" in out.stdout


def resolve_stockfish_path(path: str, probe=None) -> str:
    """
    Accept a folder or full path. In a folder: `stockfish(.exe)` if present, else the fastest
    release build by name that `probe` (default: none, trust the ranking) says runs here.
    """
    candidate = Path(path)
    if candidate.is_file():
        return str(candidate)

    if candidate.is_dir():
        for name in ("stockfish.exe", "stockfish"):
            exe = candidate / name
            if exe.is_file():
                return str(exe)
        builds = sorted(
            (p for p in candidate.glob("stockfish*") if p.is_file() and p.suffix in ("", ".exe")),
            key=lambda p: (build_rank(p.name), p.name),
        )
        for build in builds:
            if probe is None or probe(str(build)):
                return str(build)
        if builds:
            return str(builds[0])

    return path


_resolved: dict[str, str] = {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    stockfish_path: str = str(DEFAULT_STOCKFISH_DIR)
    chess_com_api_base: str = "https://api.chess.com/pub"
    lichess_api_base: str = "https://lichess.org/api"
    analysis_depth: int = 18
    # The web app, and the Expo app when run in a browser (`npx expo start --web`).
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8081"]

    # Multi-user: when true every request needs a Supabase access token. When false
    # (local-first default) a token is still honoured if one is sent.
    auth_required: bool = False
    # Durable per-user analysis queue (needs the analysis_jobs migration). Off: BackgroundTasks.
    job_queue_enabled: bool = False
    job_poll_seconds: float = 2.0
    # Automatic sync of new finished games for the usernames saved in Settings (services/sync.py).
    auto_sync_enabled: bool = False
    sync_minutes: float = 5.0
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
    # Games analysed at once, one single-threaded engine each; 0 = one per core, leaving one free.
    analysis_workers: int = 0
    safe_set_tol: float = 0.05
    ep_decided_low: float = 0.05
    ep_decided_high: float = 0.95
    # Human move model behind services/human_model.py (docs/adr/0002-human-model.md).
    # "auto" uses Maia-2 when the optional package is installed (requirements-maia.txt)
    # and the heuristic otherwise; "maia2" and "heuristic" force one.
    human_model: str = "auto"
    maia2_model_type: str = "blitz"  # "blitz" or "rapid"
    maia2_cache_dir: str = ".cache/maia2"
    # Intention tagger (M7): engine-free motif tags and idea windows. Off until the
    # intention_tags migration is applied.
    idea_tagger_enabled: bool = False

    # Brilliant detection thresholds (tunable)
    brilliant_eval_margin: float = 0.3
    brilliant_winning_margin: float = 3.0

    @property
    def workers(self) -> int:
        import os

        return self.analysis_workers if self.analysis_workers > 0 else max(1, (os.cpu_count() or 2) - 1)

    @property
    def stockfish_executable(self) -> str:
        """Resolved once per path: probing builds starts processes, so it is not repeated per game."""
        if self.stockfish_path not in _resolved:
            _resolved[self.stockfish_path] = resolve_stockfish_path(self.stockfish_path, probe=build_runs)
        return _resolved[self.stockfish_path]


settings = Settings()
