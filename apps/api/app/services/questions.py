"""
After-game questions and today's intention (docs/DESIGN.md, Summary).

- Rotation: at most `budget` questions per game (Settings: 0, 1 or 2), rotating between
  "Did this game feel like you?", the intent prompt on a moment and a random check-in. The start of
  the rotation is fixed per game, so reloading a summary asks the same thing.
- Check-in: asks "Was something going on here?" about a move the distraction detector flagged, or,
  on games without a flag, about a deterministic random control move, so the detector's flags can be
  tested against moves it did not flag.
- Intention: "Today I want to…" set in Play before the game is graded here, first, and only after the
  game; it is never shown during a game.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

ROTATION = ["felt", "intent", "checkin"]
CHECKIN_ANSWERS = ("distracted", "time_pressure", "on_purpose", "nothing")
INTENT_LABELS = {"sacrifice": "look for a sacrifice", "calm": "stay calm when attacked", "solid": "just play solid"}
INTENT_WINDOW = timedelta(hours=24)


def _seed(game_id: str) -> int:
    return int(hashlib.sha256(game_id.encode()).hexdigest()[:8], 16)


def rotation(game_id: str, budget: int) -> list[str]:
    """The question kinds for this game, in order, `budget` long (0–2)."""
    budget = max(0, min(2, budget))
    start = _seed(game_id) % len(ROTATION)
    return [ROTATION[(start + i) % len(ROTATION)] for i in range(budget)]


def checkin_target(game_id: str, flagged: list[int], user_plies: list[int]) -> tuple[int | None, bool]:
    """(ply, flagged?) for the check-in: a flagged move first, else a deterministic control move."""
    if flagged:
        return flagged[0], True
    if not user_plies:
        return None, False
    return user_plies[_seed(game_id + ":control") % len(user_plies)], False


def intention_for(intents: list[dict], played_at: str | None) -> str | None:
    """The intention set most recently before the game, within the day before it."""
    if not played_at:
        return None
    when = datetime.fromisoformat(played_at.replace("Z", "+00:00"))
    best = None
    for row in intents:
        set_at = datetime.fromisoformat(row["set_at"].replace("Z", "+00:00"))
        if when - INTENT_WINDOW <= set_at <= when and (best is None or set_at > best[0]):
            best = (set_at, row["value"])
    return best[1] if best else None


def grade_intention(intent: str | None, offers: list[str], survived: int, missed: int, unsound: int, costly: int) -> dict | None:
    """
    How the game went against the intention. `offers` are labels of genuine sacrifices played,
    `costly` the moves classed mistake or worse. Mirrors, never grades the player as failing.
    """
    if intent not in INTENT_LABELS:
        return None
    label = INTENT_LABELS[intent]
    if intent == "sacrifice":
        met = bool(offers)
        line = f"You offered material on {offers[0]}." if met else "No sacrifice this time. The chance may still be in your review."
    elif intent == "calm":
        faced = survived + missed
        met = None if faced == 0 else survived >= missed
        line = (
            "No real problems were set for you this game."
            if faced == 0
            else f"You found the safe reply {survived} of {faced} times."
        )
    else:
        met = unsound == 0 and costly == 0
        line = "A solid game: no unsound chaos and nothing costly." if met else f"{unsound + costly} moves went beyond solid. They're in your review."
    return {"intent": intent, "label": label, "met": met, "line": line}
