"""
Player settings (docs/DESIGN.md, screen 10): the style goal (profiles.style_goal) and the other
preferences (profiles.settings jsonb), plus what Sarce keeps and the journal export.

Validation lives here so the jsonb column only ever holds known keys and values.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.db.supabase import get_supabase
from app.services.library import LibraryService
from app.services.summary import move_label

DEFAULTS = {
    "questionBudget": 1,
    "quietUntil": None,
    "sources": "both",
    "theme": "light",
    "playfulMascot": True,
    "motion": "system",
}
CHOICES = {
    "questionBudget": {0, 1, 2},
    "sources": {"chess_com", "lichess", "both"},
    "theme": {"light", "system"},
    "motion": {"system", "full", "reduced"},
}
GOAL_MIN, GOAL_MAX = 0, 15


def validate(changes: dict) -> dict:
    """Known keys only, each with an allowed value; raises ValueError otherwise."""
    clean = {}
    for key, value in changes.items():
        if key in ("goalLo", "goalHi"):
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not GOAL_MIN <= value <= GOAL_MAX:
                raise ValueError(f"{key} must be a number from {GOAL_MIN} to {GOAL_MAX}")
            clean[key] = value
        elif key in CHOICES:
            if value not in CHOICES[key]:
                raise ValueError(f"{key} must be one of {sorted(CHOICES[key], key=str)}")
            clean[key] = value
        elif key == "quietUntil":
            if value is not None:
                date.fromisoformat(str(value))
            clean[key] = value
        elif key == "playfulMascot":
            if not isinstance(value, bool):
                raise ValueError("playfulMascot must be true or false")
            clean[key] = value
        else:
            raise ValueError(f"Unknown setting {key!r}")
    if "goalLo" in clean and "goalHi" in clean and clean["goalLo"] >= clean["goalHi"]:
        raise ValueError("goalLo must be below goalHi")
    return clean


def quiet_until(days: int = 7, today: date | None = None) -> str:
    return ((today or datetime.now(timezone.utc).date()) + timedelta(days=days)).isoformat()


class SettingsStore:
    def get(self, owner_id: str) -> dict:
        rows = get_supabase().table("profiles").select("style_goal, settings").eq("id", owner_id).limit(1).execute().data or []
        row = rows[0] if rows else {}
        goal = row.get("style_goal") or {}
        quiet = (row.get("settings") or {}).get("quietUntil")
        if quiet and date.fromisoformat(quiet) < datetime.now(timezone.utc).date():
            quiet = None  # an expired quiet week is simply over
        return {
            **DEFAULTS,
            **(row.get("settings") or {}),
            "quietUntil": quiet,
            "goalLo": goal.get("target_brilliant_min", 6),
            "goalHi": goal.get("target_brilliant_max", 10),
        }

    def update(self, owner_id: str, changes: dict) -> dict:
        current = self.get(owner_id)
        clean = validate(changes)
        lo, hi = clean.get("goalLo", current["goalLo"]), clean.get("goalHi", current["goalHi"])
        if lo >= hi:
            raise ValueError("goalLo must be below goalHi")
        prefs = {k: v for k, v in {**current, **clean}.items() if k in DEFAULTS}
        get_supabase().table("profiles").update(
            {
                "settings": prefs,
                "style_goal": {"target_brilliant_min": lo, "target_brilliant_max": hi},
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", owner_id).execute()
        return self.get(owner_id)

    def kept(self, owner_id: str, user_id: str | None) -> dict:
        sb = get_supabase()
        games = sb.table("games").select("id", count="exact").limit(1)
        if user_id:
            games = games.eq("user_id", user_id)
        notes = sb.table("move_annotations").select("id", count="exact").limit(1)
        return {"games": games.execute().count or 0, "notes": notes.execute().count or 0}

    def journal(self, owner_id: str, user_id: str | None) -> str:
        """The journal as Markdown: your sacrifices with notes, newest first, and every saved note."""
        sb = get_supabase()
        settings = self.get(owner_id)
        lines = [
            "# Sarce journal",
            "",
            f"Style goal: {settings['goalLo']}–{settings['goalHi']}% Brilliant. Exported {datetime.now(timezone.utc).date().isoformat()}.",
            "",
            "## Sacrifices",
            "",
        ]
        for row in LibraryService().sacrifices(user_id, None, limit=500):
            when = (row.get("playedAt") or "")[:10]
            outcome = "held" if row["held"] else "didn't hold"
            lines.append(f"- {when} · {row['label']} vs {row.get('opponent') or 'opponent'} · {row['type']} −{row['material']} · {outcome}")
            if row.get("note"):
                lines.append(f"  - Note: {row['note']}")
        notes = sb.table("move_annotations").select("game_id, ply, intent_type, note, games!inner(opponent, played_at, user_id)").execute().data or []
        if user_id:
            notes = [n for n in notes if (n.get("games") or {}).get("user_id") == user_id]
        lines += ["", "## Notes on moments", ""]
        for n in sorted(notes, key=lambda n: (n.get("games") or {}).get("played_at") or "", reverse=True):
            game = n.get("games") or {}
            kind = f" ({n['intent_type']})" if n.get("intent_type") else ""
            lines.append(f"- {(game.get('played_at') or '')[:10]} · {move_label(n['ply'], None).strip()} vs {game.get('opponent') or 'opponent'}{kind}: {n.get('note') or ''}")
        if not notes:
            lines.append("No notes yet.")
        return "\n".join(lines) + "\n"
