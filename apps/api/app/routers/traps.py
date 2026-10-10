from fastapi import APIRouter, HTTPException, Query

from app.services.trap_atlas import TrapAtlasService

router = APIRouter()
trap_atlas_service = TrapAtlasService()


@router.get("")
async def list_traps(
    band: int | None = Query(None, ge=0, le=4000, description="Lower edge of a 200-point rating band"),
    eco: str | None = Query(None, max_length=3, pattern="^[A-Ea-e][0-9]{0,2}$"),
    limit: int = Query(50, ge=1, le=200),
):
    """Positions where the most common reply at a rating band loses heavily."""
    try:
        traps = trap_atlas_service.list_traps(band=band, eco=eco.upper() if eco else None, limit=limit)
        return {"traps": traps}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
