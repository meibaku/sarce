from fastapi import APIRouter, HTTPException, Query

from app.deps import current_user_id, scoped_user_id

from app.services.chess_com import normalize_chess_com_username
from app.services.home import HomeService
from app.services.lens_service import LensService
from app.services.you import YouService

router = APIRouter()
lens_service = LensService()
home_service = HomeService()
you_service = YouService()


@router.get("/home")
async def get_home(username: str | None = Query(None), user_id: str | None = Query(None)):
    """Home screen: the latest game's style read and moments, and the Brilliant card."""
    name = normalize_chess_com_username(username) if username else None
    try:
        return home_service.home(scoped_user_id(user_id, username), name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/you")
async def get_you(username: str | None = Query(None), user_id: str | None = Query(None)):
    """You: Brilliant trend and formula, style fingerprint, reference axes, time controls, survival."""
    name = normalize_chess_com_username(username) if username else None
    try:
        return you_service.you(scoped_user_id(user_id, username), name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{username}/chaos-summary")
async def get_chaos_summary(username: str):
    """Counts of real / cheap / calculated chaos and the survival rate for a player."""
    try:
        return lens_service.chaos_summary(
            normalize_chess_com_username(username), user_id=current_user_id()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
