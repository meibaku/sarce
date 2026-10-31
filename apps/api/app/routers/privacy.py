"""Participant portability and erasure remain available after pilot withdrawal."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.deps import current_user_id
from app.services.privacy import PrivacyService

router = APIRouter()
public_router = APIRouter()


def owner_id() -> str:
    owner = current_user_id()
    if not owner:
        raise HTTPException(status_code=401, detail="Sign in required")
    return owner


@router.get("/me/export")
async def export_account():
    owner = owner_id()
    return JSONResponse(
        PrivacyService().export(owner),
        headers={"Content-Disposition": 'attachment; filename="sarce-account-export.json"'},
    )


@router.delete("/me")
async def delete_account(confirm: str = Query(...)):
    if confirm != "DELETE":
        raise HTTPException(status_code=422, detail="Set confirm=DELETE to erase the account")
    owner = owner_id()
    try:
        return PrivacyService().start_deletion(owner)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@public_router.get("/deletions/{job_id}")
async def deletion_status(job_id: str, receipt: str = Query(..., min_length=24, max_length=200)):
    row = PrivacyService().deletion_status(job_id, receipt)
    if not row:
        raise HTTPException(status_code=404, detail="Deletion receipt not found")
    return row
