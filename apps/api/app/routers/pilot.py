"""Invite, consent, feedback and withdrawal routes for the style pilot."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.deps import current_user_id
from app.services.pilot import PilotService
from app.services.pilot_policy import PilotPolicy

router = APIRouter()
public_router = APIRouter()


def user_id() -> str:
    user = current_user_id()
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def operator_id() -> str:
    user = user_id()
    if user not in settings.pilot_operators:
        raise HTTPException(status_code=403, detail="Pilot operator access required")
    return user


class InvitationRequest(BaseModel):
    hours: int = Field(168, ge=1, le=24 * 30)


class RedeemRequest(BaseModel):
    token: str = Field(..., min_length=24, max_length=200)


class ConsentRequest(BaseModel):
    adultConfirmed: bool
    protocolVersion: str = Field(..., max_length=80)
    privacyVersion: str = Field(..., max_length=80)


class FeedbackRequest(BaseModel):
    resonance: str = Field(..., pattern="^(yes|partly|no)$")
    comment: str | None = Field(None, max_length=500)


class ExitSurveyRequest(BaseModel):
    continueUsing: str = Field(..., pattern="^(yes|maybe|no)$")
    mostValuable: str = Field(..., min_length=1, max_length=120)
    leastTrusted: str = Field(..., min_length=1, max_length=120)
    willingnessToPay: str = Field(..., pattern="^(yes|maybe|no)$")


def invalid(call):
    try:
        return call()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@public_router.get("")
async def public_mode():
    """Let the web choose its shell without requiring a participant session."""
    return {
        **PilotPolicy.current().public(),
        "backupRetentionDays": settings.pilot_backup_retention_days,
    }


@router.post("/invitations")
async def create_invitation(body: InvitationRequest):
    operator = operator_id()
    return PilotService().create_invitation(operator, body.hours)


@router.post("/invitations/redeem")
async def redeem_invitation(body: RedeemRequest):
    owner = user_id()
    return invalid(lambda: PilotService().redeem(owner, body.token))


@router.post("/consent")
async def record_consent(body: ConsentRequest):
    owner = user_id()
    return invalid(lambda: PilotService().consent(
        owner, body.adultConfirmed, body.protocolVersion, body.privacyVersion
    ))


@router.get("/status")
async def status():
    owner = user_id()
    return PilotService().status(owner)


@router.post("/withdraw")
async def withdraw():
    owner = user_id()
    return invalid(lambda: PilotService().withdraw(owner))


@router.put("/games/{game_id}/feedback")
async def feedback(game_id: str, body: FeedbackRequest):
    owner = user_id()
    return invalid(lambda: PilotService().feedback(owner, game_id, body.resonance, body.comment))


@router.get("/games/{game_id}/feedback")
async def get_feedback(game_id: str):
    owner = user_id()
    return invalid(lambda: PilotService().get_feedback(owner, game_id))


@router.put("/exit-survey")
async def exit_survey(body: ExitSurveyRequest):
    owner = user_id()
    return PilotService().exit_survey(owner, {
        "continue_using": body.continueUsing,
        "most_valuable": body.mostValuable,
        "least_trusted": body.leastTrusted,
        "willingness_to_pay": body.willingnessToPay,
    })
