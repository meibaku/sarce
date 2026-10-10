from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.deps import resolve_user_id
from app.services.scouting import ScoutingService

router = APIRouter()
scouting_service = ScoutingService()

Source = Literal["chess_com", "lichess"]


class ScoutRequest(BaseModel):
    """Scout one player the user names. Finished public games only."""

    username: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\- ]+$")
    source: Source = "chess_com"
    user_id: str | None = None
    max_games: int = Field(default=50, ge=1, le=100)


@router.post("/reports")
async def create_report(body: ScoutRequest):
    """Build a private preparation report from a named player's recent finished games."""
    try:
        return await scouting_service.create_report(
            owner_user_id=resolve_user_id(body.user_id),
            username=body.username,
            source=body.source,
            max_games=body.max_games,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Scouting failed: {exc}") from exc


@router.get("/reports")
async def list_reports(user_id: str | None = Query(None)):
    """The caller's own reports. There is no way to list other people's."""
    try:
        return {"reports": scouting_service.list_reports(resolve_user_id(user_id))}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/reports/{report_id}")
async def delete_report(report_id: str, user_id: str | None = Query(None)):
    if not scouting_service.delete_report(resolve_user_id(user_id), report_id):
        raise HTTPException(status_code=404, detail="Report not found")
    return {"deleted": 1}


@router.delete("/targets/{source}/{username}")
async def delete_target(source: Source, username: str):
    """Deletion on request: remove every stored report about this player."""
    return {"deleted": scouting_service.delete_target(source, username)}
