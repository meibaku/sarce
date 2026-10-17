from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.deps import current_user_id, resolve_user_id, scoped_user_id

from app.services.chess_com import normalize_chess_com_username
from app.services.home import HomeService
from app.services.lens_service import LensService
from app.services.library import LibraryService
from app.services.recap import INTENTS, FOCUSES, RecapService
from app.services.you import YouService

router = APIRouter()
lens_service = LensService()
home_service = HomeService()
you_service = YouService()
library_service = LibraryService()
recap_service = RecapService()


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


@router.get("/sacrifices")
async def get_sacrifices(username: str | None = Query(None), user_id: str | None = Query(None)):
    """Sacrifice library: every sacrifice played, newest first, with what was offered and the note."""
    name = normalize_chess_com_username(username) if username else None
    try:
        return {"sacrifices": library_service.sacrifices(scoped_user_id(user_id, username), name)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class FocusRequest(BaseModel):
    kind: str
    value: str


@router.get("/recap")
async def get_recap(user_id: str | None = Query(None)):
    """Weekly recap: the week's games, Brilliant, best moment, last focus and next week's options."""
    data = recap_service.recap(scoped_user_id(user_id, None), resolve_user_id(user_id))
    if data is None:
        raise HTTPException(status_code=404, detail="No analysed games yet")
    return data


@router.get("/focus")
async def get_focus(user_id: str | None = Query(None)):
    """The current weekly focus and today's intention, with the choices for each."""
    owner = resolve_user_id(user_id)
    return {
        "weekly": recap_service.current_focus(owner, "weekly"),
        "today": recap_service.current_focus(owner, "today"),
        "focuses": FOCUSES,
        "intents": INTENTS,
    }


@router.put("/focus")
async def set_focus(body: FocusRequest, user_id: str | None = Query(None)):
    """Sets next week's focus (kind=weekly) or today's intention (kind=today)."""
    if body.kind not in ("weekly", "today"):
        raise HTTPException(status_code=422, detail="kind must be weekly or today")
    try:
        return recap_service.set_focus(resolve_user_id(user_id), body.kind, body.value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{username}/chaos-summary")
async def get_chaos_summary(username: str):
    """Counts of real / cheap / calculated chaos and the survival rate for a player."""
    try:
        return lens_service.chaos_summary(
            normalize_chess_com_username(username), user_id=current_user_id()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
