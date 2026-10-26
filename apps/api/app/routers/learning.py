"""Thin HTTP boundary for Learning Evidence admission and participant state."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AwareDatetime, BaseModel, Field

from app.config import settings
from app.deps import current_user_id
from app.services.learning_admission import LearningAdmissionStore, prepare_invite_batch

router = APIRouter()
store = LearningAdmissionStore()


def require_signed_in_user() -> str:
    """Research consent always binds to a verified Supabase identity, even in local-first mode."""
    user_id = current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in to join Learning Evidence")
    return user_id


def require_learning_operator(user_id: str = Depends(require_signed_in_user)) -> str:
    if user_id not in settings.learning_operators:
        raise HTTPException(status_code=403, detail="Learning invitations are restricted to study operators")
    return user_id


class InviteBatchRequest(BaseModel):
    count: int = Field(ge=2, le=200)
    protocolVersion: int = Field(default=1, ge=1)
    cohort: str = "controlled"
    expiresInHours: int = Field(default=168, ge=1, le=720)


class EnrollRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    adultConfirmed: bool
    consentedAt: AwareDatetime


@router.post("/invites/batches")
async def create_invite_batch(body: InviteBatchRequest, operator: str = Depends(require_learning_operator)):
    try:
        batch, invites, tokens = prepare_invite_batch(
            created_by=operator, count=body.count, protocol_version=body.protocolVersion,
            cohort=body.cohort, expires_in_hours=body.expiresInHours,
        )
        await asyncio.to_thread(store.create_batch, batch, invites)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"batchId": batch["id"], "expiresAt": batch["expires_at"], "tokens": tokens}


@router.post("/enrol")
async def enrol(body: EnrollRequest, user_id: str = Depends(require_signed_in_user)):
    if body.consentedAt > datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Consent time cannot be in the future")
    try:
        return await asyncio.to_thread(
            store.enroll, token=body.token, user_id=user_id,
            adult_confirmed=body.adultConfirmed, consented_at=body.consentedAt,
        )
    except Exception as exc:
        # Do not reveal whether a token exists, expired, or was previously redeemed.
        raise HTTPException(status_code=409, detail="Invitation is invalid, expired, or already used") from exc


@router.get("/status")
async def status(user_id: str = Depends(require_signed_in_user)):
    enrollment = await asyncio.to_thread(store.status, user_id)
    return {"enrolled": enrollment is not None, "enrollment": enrollment}


@router.post("/withdraw")
async def withdraw(user_id: str = Depends(require_signed_in_user)):
    enrollment = await asyncio.to_thread(store.withdraw, user_id, datetime.now(timezone.utc))
    if not enrollment:
        raise HTTPException(status_code=404, detail="Learning enrollment not found")
    return {"withdrawn": enrollment.get("withdrawn_at") is not None, "enrollment": enrollment}
