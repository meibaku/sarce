"""Authoritative feature boundary for the invite-only style pilot."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from app.config import settings


CORE_STYLE_CAPABILITIES = frozenset(
    {
        "brilliant",
        "games",
        "journal",
        "move_classification",
        "pilot_feedback",
        "privacy",
        "saved_positions",
    }
)

EXPERIMENTAL_CAPABILITIES = frozenset(
    {
        "chaos",
        "focus",
        "opponent_prep",
        "quests",
        "references",
        "style_fingerprint",
        "traps",
    }
)


@dataclass(frozen=True)
class PilotPolicy:
    """Keep API and clients on one fail-closed pilot capability contract."""

    mode: str

    @classmethod
    def current(cls) -> "PilotPolicy":
        return cls(settings.pilot_mode)

    @property
    def enabled(self) -> bool:
        return self.mode == "style_v1"

    def allows(self, capability: str) -> bool:
        if not self.enabled:
            return True
        return capability in CORE_STYLE_CAPABILITIES

    def public(self) -> dict:
        visible = CORE_STYLE_CAPABILITIES if self.enabled else CORE_STYLE_CAPABILITIES | EXPERIMENTAL_CAPABILITIES
        return {
            "mode": self.mode,
            "inviteOnly": self.enabled,
            "capabilities": sorted(visible),
            "experimentalHidden": self.enabled,
            "protocolVersion": settings.pilot_protocol_version if self.enabled else None,
            "privacyVersion": settings.pilot_privacy_version if self.enabled else None,
            "admissionOpen": settings.pilot_admission_open if self.enabled else False,
        }

    def require(self, capability: str) -> None:
        """Reject unavailable pilot features even when a client knows an old route."""
        if not self.allows(capability):
            raise HTTPException(status_code=404, detail="This feature is not part of the admitted style pilot")

    def filter_home(self, payload: dict) -> dict:
        if not self.enabled:
            return payload
        latest = payload.get("latest")
        if latest:
            latest = {**latest, "chaos": [], "highlight": None}
        return {**payload, "latest": latest, "focus": None, "stats": None}

    def filter_review(self, payload: dict) -> dict:
        """Retain the Brilliant review while withholding unvalidated lens narratives."""
        if not self.enabled:
            return payload
        return {**payload, "closingOut": [], "fightingBack": [], "theirIdeas": [], "ideas": []}

    def filter_explanation(self, payload: dict) -> dict:
        if not self.enabled:
            return payload
        return {**payload, "chaos": None}
