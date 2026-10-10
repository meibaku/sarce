import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.deps import authenticate
from app.routers import analysis, games, health, reference, scouting, traps, users
from app.services.job_queue import JobQueue, analysis_handlers, worker_loop


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run the analysis job worker alongside the API when the queue is enabled."""
    worker = None
    if settings.job_queue_enabled:
        handlers = analysis_handlers(games.analysis_service.analyze_pending)
        worker = asyncio.create_task(worker_loop(JobQueue(), handlers, settings.job_poll_seconds))
    try:
        yield
    finally:
        if worker:
            worker.cancel()

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
