"""
One focus a week (implementation plan 3.2).

Home names one trait for the week, the one with the most room: the trait whose last RECENT_GAMES games sit lowest
among twelve WINDOW-game stretches of your own history. Stretches of games rather than calendar weeks, because
players play in bursts: a busy week can hold 250 games and a quiet month none. Brilliant is never the focus, since it stays the headline (ADR 0001; ADR 0003's
"a focus changes emphasis, not the headline" carries over). A trait you pick yourself in the Recap
(`user_focus`, kind `weekly`, value `trait:<Name>`) wins over the automatic pick.

The target comes from your own data, so it is reachable (review F4): the upper end of the trait's 95% range over
the last RECENT_GAMES games for share traits, the 75th percentile of your stretches for Initiative. The Recap says
whether this week's games moved it, and only "up" or "down" when their range separates from the RECENT_GAMES games
before them; otherwise "held".
"""

from __future__ import annotations

import time
from datetime import datetime

from app.db.supabase import get_supabase
from app.services.uncertainty import direction, wilson
from app.services.you import SHARE_TRAITS, TRAIT_PHRASE, TRAITS, YouService, gated_traits

WINDOW = 40  # games per stretch of history
WINDOWS = 12
RECENT_GAMES = 80  # what "now" pools
MIN_WINDOWS = 6  # stretches with a value a trait needs before it can be the focus
WEEK_S = 7 * 86400
GAMES_READ = 1000
PREFIX = "trait:"
CACHE_S = 600
_cache: dict[str, tuple[float, dict | None]] = {}


def windows_of(ids_newest_first: list[str]) -> list[list[str]]:
    """Up to WINDOWS stretches of WINDOW games, oldest first."""
    ids = ids_newest_first[: WINDOW * WINDOWS]
    return [ids[i : i + WINDOW] for i in range(0, len(ids), WINDOW)][::-1]


def this_week(games_newest_first: list[dict]) -> list[str]:
    """Ids of the games in the seven days up to your latest game."""
    if not games_newest_first:
        return []
    latest = datetime.fromisoformat(games_newest_first[0]["played_at"].replace("Z", "+00:00"))
    return [
        g["id"] for g in games_newest_first
        if (latest - datetime.fromisoformat(g["played_at"].replace("Z", "+00:00"))).total_seconds() < WEEK_S
    ]


def trait_from_focus(value: str | None) -> str | None:
    if value and value.startswith(PREFIX) and value[len(PREFIX):] in TRAITS:
        return value[len(PREFIX):]
    return None


def percentile_of(value: float, values: list[float]) -> float:
    """Share of `values` below `value` (0 = lowest week, 1 = highest)."""
    return sum(1 for v in values if v < value) / len(values) if values else 0.5


def pick_trait(stretches: dict[str, list[float | None]], recent: dict[str, float | None]) -> str | None:
    """The trait whose recent value sits lowest among your own stretches; traits with too few are skipped."""
    best, best_pct = None, 2.0
    for t in TRAITS:
        weeks = [v for v in stretches.get(t, []) if v is not None]
        if len(weeks) < MIN_WINDOWS or recent.get(t) is None:
            continue
        pct = percentile_of(recent[t], weeks)
        if pct < best_pct:
            best, best_pct = t, pct
    return best


def target_for(trait: str, recent_value: float, recent_events: int, weeks: list[float]) -> float:
    """A reachable aim from your own data: the 95% range's upper end (shares) or your 75th-percentile stretch."""
    if trait in SHARE_TRAITS and recent_events:
        hi = wilson(recent_value * recent_events, recent_events)[1]
        return round(max(recent_value, hi), 4)
    ranked = sorted(weeks)
    return round(max(recent_value, ranked[int(0.75 * (len(ranked) - 1))]), 4)


def week_verdict(trait: str, this_week: tuple[float | None, int], before: tuple[float | None, int]) -> str:
    """"up", "down" or "held": a direction only when the two ranges separate (shares); otherwise held."""
    (v1, n1), (v0, n0) = this_week, before
    if trait not in SHARE_TRAITS or v1 is None or v0 is None or not n1 or not n0:
        return "held"
    return direction(wilson(v0 * n0, n0), wilson(v1 * n1, n1)) or "held"


class FocusService:
    def weekly(self, user_id: str | None, chosen: str | None, username: str | None = None) -> dict | None:
        """This week's focus for Home and Recap: {trait, phrase, value, target, auto, verdict, …}; None without data."""
        key = f"{user_id}|{username}|{chosen}"
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_S:
            return hit[1]
        result = self._compute(user_id, chosen, username)
        _cache[key] = (time.monotonic(), result)
        return result

    def _compute(self, user_id: str | None, chosen: str | None, username: str | None = None) -> dict | None:
        sb = get_supabase()
        q = (
            sb.table("games").select("id, played_at").eq("analysis_status", "complete").neq("source", "sarce_bot")
            .order("played_at", desc=True).limit(GAMES_READ)
        )
        if user_id:
            q = q.eq("user_id", user_id)
        if username:  # the same scope as the rest of Home
            q = q.eq("chess_com_username", username)
        games = [g for g in (q.execute().data or []) if g.get("played_at")]
        if not games:
            return None
        ids = [g["id"] for g in games]
        windows = windows_of(ids)
        week_ids = this_week(games)
        # Everything the stretches, "now", this week and the games before it read; a busy week reaches further back.
        _, _, moves, lens = YouService()._load(ids[: max(WINDOW * WINDOWS, len(week_ids) + RECENT_GAMES)])

        def traits_for(group: list[str]) -> tuple[dict, dict]:
            return gated_traits([m for i in group for m in moves.get(i, [])], [r for i in group for r in lens.get(i, [])])

        stretch_values = [traits_for(w)[0] for w in windows]
        stretches = {t: [w[t] for w in stretch_values] for t in TRAITS}
        recent, recent_events = traits_for(ids[:RECENT_GAMES])

        trait = trait_from_focus(chosen) or pick_trait(stretches, recent)
        if trait is None or recent.get(trait) is None:
            return None
        values = [v for v in stretches[trait] if v is not None]
        week, week_events = traits_for(week_ids)
        before, before_events = traits_for(ids[len(week_ids) : len(week_ids) + RECENT_GAMES])
        return {
            "trait": trait,
            "phrase": TRAIT_PHRASE[trait],
            # Four decimals: a rare trait (Sacrifice at 0.3%) must survive until the client formats it.
            "value": round(recent[trait], 4),
            "games": RECENT_GAMES,
            "unit": "share" if trait in SHARE_TRAITS else "score",  # shares read as percentages
            "target": target_for(trait, recent[trait], recent_events[trait], values or [recent[trait]]),
            "auto": trait_from_focus(chosen) is None,
            "verdict": week_verdict(trait, (week[trait], week_events[trait]), (before[trait], before_events[trait])),
            # The verdict's own samples: this week's games against the RECENT_GAMES before them.
            "week": None if week[trait] is None else round(week[trait], 4),
            "before": None if before[trait] is None else round(before[trait], 4),
        }
