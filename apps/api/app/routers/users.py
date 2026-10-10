from fastapi import APIRouter, HTTPException

from app.services.chess_com import normalize_chess_com_username
from app.services.lens_service import LensService

router = APIRouter()
lens_service = LensService()


@router.get("/{username}/chaos-summary")
async def get_chaos_summary(username: str):
    """Counts of real / cheap / calculated chaos and the survival rate for a player."""
    try:
        return lens_service.chaos_summary(normalize_chess_com_username(username))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
