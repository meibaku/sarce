from fastapi import APIRouter, BackgroundTasks, Query

from app.services.reference import ReferenceService

router = APIRouter()
reference_service = ReferenceService()


@router.get("/tal")
async def get_tal_benchmark():
    """Cached Mikhail Tal reference benchmark (Brilliant % + distribution)."""
    return await reference_service.get_tal_benchmark()


@router.post("/tal/process")
async def process_tal_benchmark(
    background_tasks: BackgroundTasks,
    max_games: int = Query(5, ge=1, le=50, description="Limit for local dev speed"),
):
    """
    One-time batch: download Tal PGN corpus, classify, cache results.

    Run manually or via: python -m scripts.process_tal_benchmark
    """

    async def run():
        await reference_service.process_tal_benchmark(max_games=max_games)

    background_tasks.add_task(run)
    return {"message": f"Tal benchmark processing started ({max_games} games)"}
