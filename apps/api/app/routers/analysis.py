from fastapi import APIRouter, HTTPException, Query

from app.deps import resolve_user_id
from app.services.chess_com import normalize_chess_com_username
from app.services.baseline import BaselineService
from app.services.style_profile import StyleProfileService

router = APIRouter()
baseline_service = BaselineService()
style_profile_service = StyleProfileService()


@router.get("/baseline/{user_id}")
async def get_baseline(
    user_id: str,
    username: str | None = Query(None, description="Chess.com username for local dev"),
):
    """
    Rolling move-quality baseline for a user.

    Returns Brilliant %, full distribution, games analyzed, and target range.
    """
    try:
        return await baseline_service.get_user_baseline(
            user_id=resolve_user_id(user_id),
            chess_com_username=username,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/timeline/{user_id}")
async def get_timeline(
    user_id: str,
    username: str | None = Query(None),
):
    """Brilliant % per game over time — powers the dashboard line chart."""
    try:
        points = await baseline_service.get_timeline(
            user_id=resolve_user_id(user_id),
            chess_com_username=username,
        )
        return {"points": points}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/style-profile/{user_id}")
async def get_style_profile(
    user_id: str,
    username: str | None = Query(None),
):
    """Aggregated player style: openings, phases, results, and tactical signals."""
    try:
        return await style_profile_service.get_profile(
            user_id=resolve_user_id(user_id),
            chess_com_username=normalize_chess_com_username(username) if username else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
