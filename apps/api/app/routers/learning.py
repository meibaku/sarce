"""Thin HTTP boundary for Learning Evidence admission and participant state."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AwareDatetime, BaseModel, Field

from app.config import settings
from app.deps import current_user_id
from app.services.learning_admission import LearningAdmissionStore, prepare_invite_batch
from app.services.learning_sessions import LearningSessionStore
from app.services.learning_review import LearningReviewStore

router = APIRouter()
admission_store = LearningAdmissionStore()
session_store = LearningSessionStore()
review_store = LearningReviewStore()


def participant_enrollment(enrollment: dict) -> dict:
    """Participant-safe state deliberately omits the concealed study arm and pseudonymous key."""
    return {
        "id": enrollment["id"],
        "protocolVersion": enrollment["protocol_version"],
        "cohort": enrollment["cohort"],
        "consentedAt": enrollment["consented_at"],
        "enrolledAt": enrollment["enrolled_at"],
        "withdrawnAt": enrollment.get("withdrawn_at"),
    }


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


def require_learning_reviewer(user_id: str = Depends(require_signed_in_user)) -> str:
    if user_id not in {*settings.learning_reviewers, *settings.learning_operators}:
        raise HTTPException(status_code=403, detail="Learning item review is restricted to configured reviewers")
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
        await asyncio.to_thread(admission_store.create_batch, batch, invites)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"batchId": batch["id"], "expiresAt": batch["expires_at"], "tokens": tokens}


@router.post("/enrol")
async def enrol(body: EnrollRequest, user_id: str = Depends(require_signed_in_user)):
    if body.consentedAt > datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Consent time cannot be in the future")
    try:
        enrollment = await asyncio.to_thread(
            admission_store.enroll, token=body.token, user_id=user_id,
            adult_confirmed=body.adultConfirmed, consented_at=body.consentedAt,
        )
    except Exception as exc:
        # Do not reveal whether a token exists, expired, or was previously redeemed.
        raise HTTPException(status_code=409, detail="Invitation is invalid, expired, or already used") from exc
    return participant_enrollment(enrollment)


@router.get("/status")
async def status(user_id: str = Depends(require_signed_in_user)):
    enrollment = await asyncio.to_thread(admission_store.status, user_id)
    sessions = await asyncio.to_thread(session_store.progress, enrollment["id"]) if enrollment else []
    return {
        "enrolled": enrollment is not None,
        "enrollment": participant_enrollment(enrollment) if enrollment else None,
        "sessions": sessions,
    }


@router.post("/withdraw")
async def withdraw(user_id: str = Depends(require_signed_in_user)):
    enrollment = await asyncio.to_thread(admission_store.withdraw, user_id, datetime.now(timezone.utc))
    if not enrollment:
        raise HTTPException(status_code=404, detail="Learning enrollment not found")
    return {
        "withdrawn": enrollment.get("withdrawn_at") is not None,
        "enrollment": participant_enrollment(enrollment),
    }


class SessionRequest(BaseModel):
    phase: str


class AttemptRequest(BaseModel):
    clientAttemptId: str = Field(min_length=36, max_length=36)
    response: dict
    assistance: str = "independent"
    confidence: int | None = Field(default=None, ge=1, le=5)
    latencyMs: int = Field(ge=0, le=3_600_000)


@router.post("/sessions")
async def create_session(body: SessionRequest, user_id: str = Depends(require_signed_in_user)):
    try:
        session = await asyncio.to_thread(session_store.create, user_id, body.phase)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"sessionId": session["id"], "phase": session["phase"], "itemCount": session["item_count"]}


@router.get("/sessions/{session_id}/next")
async def next_presentation(session_id: str, user_id: str = Depends(require_signed_in_user)):
    try:
        item = await asyncio.to_thread(session_store.next, user_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"complete": item is None, "presentation": item}


@router.post("/presentations/{presentation_token}/attempt")
async def record_attempt(
    presentation_token: str, body: AttemptRequest, user_id: str = Depends(require_signed_in_user),
):
    try:
        return await asyncio.to_thread(session_store.answer, user_id, presentation_token, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/summary")
async def session_summary(session_id: str, user_id: str = Depends(require_signed_in_user)):
    try:
        return await asyncio.to_thread(session_store.summary, user_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class ReviewRequest(BaseModel):
    decision: str
    note: str = Field(default="", max_length=500)


class AdjudicateRequest(BaseModel):
    status: str


@router.get("/review/next")
async def next_review(reviewer: str = Depends(require_learning_reviewer)):
    item = await asyncio.to_thread(review_store.next, reviewer)
    return {"complete": item is None, "item": item}


@router.post("/review/{pattern_id}")
async def record_review(
    pattern_id: str, body: ReviewRequest, reviewer: str = Depends(require_learning_reviewer),
):
    try:
        return await asyncio.to_thread(review_store.annotate, pattern_id, reviewer, body.decision, body.note)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/review/metrics")
async def review_metrics(_reviewer: str = Depends(require_learning_reviewer)):
    return await asyncio.to_thread(review_store.metrics)


@router.post("/review/{pattern_id}/adjudicate")
async def adjudicate(
    pattern_id: str, body: AdjudicateRequest, _operator: str = Depends(require_learning_operator),
):
    try:
        return await asyncio.to_thread(review_store.adjudicate, pattern_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
