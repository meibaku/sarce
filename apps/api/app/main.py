from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analysis, games, health, reference

app = FastAPI(
    title="Sarce API",
    description="Chess style analysis — import, classify, benchmark",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(games.router, prefix="/games", tags=["games"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
app.include_router(reference.router, prefix="/reference", tags=["reference"])
