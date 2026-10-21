"""
Shared links (M8). `/shares` needs the owner (signed in, or the local user in single-user mode); the
public read, `/public/shares/{token}`, is mounted without the auth dependency and only ever returns the
stored snapshot.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.deps import resolve_user_id
from app.services.sharing import ShareService

router = APIRouter()
public_router = APIRouter()
service = ShareService()


class ShareRequest(BaseModel):
    kind: Literal["summary", "sacrifice"]
    gameId: str = Field(..., max_length=64)
    ply: int | None = Field(None, ge=0, le=1200)


@router.post("")
async def create_share(body: ShareRequest):
    """A read-only link to one of your games' summary or one of your sacrifices."""
    try:
        link = service.create(resolve_user_id(None), body.kind, body.gameId, body.ply)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="That game isn't yours or doesn't exist.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"id": link["id"], "token": link["token"], "kind": link["kind"]}


@router.get("")
async def list_shares():
    return {"links": service.mine(resolve_user_id(None))}


@router.delete("/{link_id}")
async def revoke_share(link_id: str):
    service.revoke(resolve_user_id(None), link_id)
    return {"revoked": link_id}


@public_router.get("/{token}")
async def read_share(token: str):
    """Anyone with the link: the snapshot taken when it was shared. 404 once revoked."""
    snapshot = service.public(token) if len(token) <= 64 else None
    if snapshot is None:
        raise HTTPException(status_code=404, detail="This link doesn't exist or was turned off.")
    return snapshot
