"""Authoritative feature boundary for the invite-only style pilot."""

from __future__ import annotations

from dataclasses import dataclass

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
        }
