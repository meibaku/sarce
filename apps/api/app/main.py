import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.deps import authenticate
from app.routers import analysis, brilliant, games, health, monitor, play, reference, scouting, shares, traps, users, videos
from app.services.sync import sync_loop
from app.services.job_queue import JobQueue, analysis_handlers, worker_loop


async def monitor_loop(every_s: float = 5) -> None:
    """The analysis monitor's tick: this machine's snapshot and alerts every few seconds, history trimmed hourly."""
    from app.services import monitor

    last_trim = 0.0
    while True:
        try:
            await asyncio.to_thread(monitor.tick, settings.workers)
            if time.monotonic() - last_trim > 3600:
                await asyncio.to_thread(monitor.trim)
                last_trim = time.monotonic()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass  # no monitor tables yet, or the database is busy: the next tick tries again
        await asyncio.sleep(every_s)


async def node_finisher_loop(poll_s: float = 20) -> None:
    """Every `poll_s`, analyse what paired nodes finished searching (fast: all cached)."""
    while True:
        try:
            await games.analysis_service.finish_node_games()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass  # the next pass tries again
        await asyncio.sleep(poll_s)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run the analysis job worker alongside the API when the queue is enabled."""
    if settings.job_queue_enabled or settings.auto_sync_enabled:
        # This process analyses games: anything a previous run left half-done goes back in the queue.
        try:
            await asyncio.to_thread(games.analysis_service.requeue_interrupted)
        except Exception:
            pass  # no database yet: the API still starts
    worker = None
    if settings.job_queue_enabled:
        handlers = analysis_handlers(games.analysis_service.analyze_pending)
        worker = asyncio.create_task(worker_loop(JobQueue(), handlers, settings.job_poll_seconds))
    ticker = asyncio.create_task(monitor_loop())
    finisher = None
    if settings.node_token:
        # Paired nodes (ADR 0010): games they finished searching are analysed here from the cache.
        finisher = asyncio.create_task(node_finisher_loop())
    syncer = None
    if settings.auto_sync_enabled:
        syncer = asyncio.create_task(
            sync_loop(users.sync_service, None, games.analysis_service.analyze_pending, settings.sync_minutes)
        )
    try:
        yield
    finally:
        if worker:
            worker.cancel()
        if syncer:
            syncer.cancel()
        if finisher:
            finisher.cancel()
        ticker.cancel()
        play.bot_service.close()

app = FastAPI(
    title="Sarce API",
    description="Chess style analysis — import, classify, benchmark",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every data router verifies the caller; /health stays open.
AUTH = [Depends(authenticate)]

app.include_router(health.router)
app.include_router(games.router, prefix="/games", tags=["games"], dependencies=AUTH)
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"], dependencies=AUTH)
app.include_router(reference.router, prefix="/reference", tags=["reference"], dependencies=AUTH)
app.include_router(users.router, prefix="/users", tags=["users"], dependencies=AUTH)
app.include_router(traps.router, prefix="/traps", tags=["traps"], dependencies=AUTH)
app.include_router(scouting.router, prefix="/scouting", tags=["scouting"], dependencies=AUTH)
app.include_router(play.router, prefix="/play", tags=["play"], dependencies=AUTH)
app.include_router(videos.router, prefix="/videos", tags=["videos"], dependencies=AUTH)
app.include_router(shares.router, prefix="/shares", tags=["shares"], dependencies=AUTH)
app.include_router(monitor.router, prefix="/monitor", tags=["monitor"], dependencies=AUTH)
# Public on purpose: anyone with a share token reads that link's stored snapshot, nothing else.
app.include_router(shares.public_router, prefix="/public/shares", tags=["shares"])
app.include_router(brilliant.public_router, prefix="/public/brilliant", tags=["brilliant"])
