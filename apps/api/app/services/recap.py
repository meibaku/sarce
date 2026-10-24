"""
Weekly recap (docs/DESIGN.md, screen 7) and the player's chosen focus.

The week is the seven days ending at the latest analysed game, so a quiet stretch still recaps
the last games played. Each game is one bar: height from its style read (v0, as on Summary),
accent when it felt like you or set a real problem. The weekly focus and today's intention are
stored in `user_focus`; the intention is graded after import and never shown during a game on
another site.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.supabase import get_supabase
from app.services.focus import FocusService
from app.services.uncertainty import direction
from app.services.home import HomeService, window_brilliant
from app.services.summary import move_label, style_read
from app.services.you import TRAIT_PHRASE, TRAITS

FOCUSES = {
    "real_problems": "Keep setting real problems",
    "calm_after_sacrifice": "Stay calm after a sacrifice",
    "safe_reply": "Find the safe reply in traps",
    # One trait for the week (plan 3.2); Home picks one automatically when none is chosen.
    **{f"trait:{t}": f"{t}: {TRAIT_PHRASE[t]}" for t in TRAITS},
}
INTENTS = {
    "sacrifice": "look for a sacrifice",
    "calm": "stay calm when attacked",
    "solid": "just play solid",
}


def week_label(start: datetime, end: datetime) -> str:
    if start.month == end.month:
        return f"{start.strftime('%b')} {start.day}–{end.day}"
    return f"{start.strftime('%b')} {start.day}–{end.strftime('%b')} {end.day}"


VERDICT = {"up": "moved up", "down": "came down", "held": "held"}


def focus_line(focus: str | None, real: int, cheap: int, survived: int, faced: int, trait_focus: dict | None = None) -> str | None:
    """How last week's focus went, in its own terms."""
    if trait_focus and focus and focus.startswith("trait:"):
        share = trait_focus.get("unit") == "share"
        fmt = (lambda v: f"{v * 100:.1f}%" if v < 0.1 else f"{v * 100:.0f}%") if share else (lambda v: f"{v:.2f}")
        line = f"{trait_focus['trait']} {VERDICT[trait_focus['verdict']]}"
        if trait_focus.get("week") is not None and trait_focus.get("before") is not None:
            # The verdict compares this week's games with the ones before them: show those two, not the 80-game value.
            line += f" this week ({fmt(trait_focus['week'])}, against {fmt(trait_focus['before'])} before)"
        return f"{line}; aiming for {fmt(trait_focus['target'])}"
    if focus == "real_problems":
        return f"Real problems: {real} set" + (f", {real / cheap:.1f} : 1 sound" if cheap else "")
    if focus == "safe_reply":
        return f"Safe replies: {survived} of {faced}" if faced else "No traps faced this week"
    if focus == "calm_after_sacrifice":
        return "Sacrifices followed by sound play" if real else "No sacrifices this week"
    return None


def streak_weeks(weeks_newest_first: list[bool]) -> int:
    count = 0
    for kept in weeks_newest_first:
        if not kept:
            break
        count += 1
    return count


class RecapService:
    def recap(self, user_id: str | None, owner_id: str) -> dict | None:
        sb = get_supabase()
        q = (
            sb.table("games")
            .select("id, played_at, felt_like_you, game_analyses(brilliant_pct, total_moves)")
            .eq("analysis_status", "complete")
            .neq("source", "sarce_bot")  # bot games are practice
            .order("played_at", desc=True)
            .limit(200)
        )
        if user_id:
            q = q.eq("user_id", user_id)
        games = q.execute().data or []
        for g in games:
            a = g.pop("game_analyses", None)
            g["analysis"] = a[0] if isinstance(a, list) and a else (a or {})
            g["when"] = datetime.fromisoformat(g["played_at"].replace("Z", "+00:00")) if g.get("played_at") else None
        games = [g for g in games if g["when"]]
        if not games:
            return None

        end = games[0]["when"]
        start = end - timedelta(days=7)
        week = [g for g in games if g["when"] > start]
        before = [g for g in games if start - timedelta(days=7) < g["when"] <= start]
        ids = [g["id"] for g in week]
        lens = sb.table("move_lens_scores").select("game_id, ply, lens, score, verdict").in_("game_id", ids).in_("lens", ["chaos", "survival"]).execute().data or []
        brilliant_moves = sb.table("game_moves").select("game_id, ply, san").in_("game_id", ids).eq("is_brilliant", True).execute().data or []

        goal = HomeService()._goal(user_id)
        bars = []
        for g in reversed(week[:12]):
            rows = [r for r in lens if r["game_id"] == g["id"] and r["lens"] == "chaos"]
            v = [r["verdict"] for r in rows]
            real, calc, cheap = v.count("real_chaos"), v.count("calculated_risk"), v.count("cheap_chaos")
            read = style_read(float(g["analysis"].get("brilliant_pct") or 0), goal["goalLo"], real, calc, cheap)
            bars.append({"gameId": g["id"], "styleRead": read, "you": g.get("felt_like_you") == "yes" or real > 0})

        chaos_rows = [r for r in lens if r["lens"] == "chaos"]
        real = sum(r["verdict"] == "real_chaos" for r in chaos_rows)
        cheap = sum(r["verdict"] == "cheap_chaos" for r in chaos_rows)
        faced = [r for r in lens if r["lens"] == "survival" and r["verdict"] in ("survived", "missed")]
        survived = sum(r["verdict"] == "survived" for r in faced)

        best = None
        if brilliant_moves:
            m = brilliant_moves[0]
            best = {"gameId": m["game_id"], "ply": m["ply"], "label": f"{move_label(m['ply'], m.get('san'))} !!"}
        elif chaos_rows:
            top = max(chaos_rows, key=lambda r: float(r.get("score") or 0))
            san = (
                sb.table("game_moves").select("san").eq("game_id", top["game_id"]).eq("ply", top["ply"]).limit(1).execute().data or [{}]
            )[0].get("san")
            best = {"gameId": top["game_id"], "ply": top["ply"], "label": f"{move_label(top['ply'], san)} · real problem"}

        this_week = window_brilliant(week)
        last_week = window_brilliant(before)
        change = None
        if this_week["pct"] is not None and last_week["pct"] is not None:
            change = round(this_week["pct"] - last_week["pct"], 1)
        # "Up" or "down" only when the weeks' intervals separate; otherwise the change may be noise (review F4).
        trend = direction(
            (last_week["lo"], last_week["hi"]) if last_week.get("lo") is not None else None,
            (this_week["lo"], this_week["hi"]) if this_week.get("lo") is not None else None,
        )

        # Weeks in a row (newest first) with at least one game that felt like you or set a real problem.
        kept = []
        for w in range(12):
            w_end = end - timedelta(days=7 * w)
            w_games = [g for g in games if w_end - timedelta(days=7) < g["when"] <= w_end]
            kept.append(any(g.get("felt_like_you") == "yes" for g in w_games) or (w == 0 and real > 0))

        weekly = self.current_focus(owner_id, "weekly")
        auto_focus = None
        if weekly is None:
            # Home's automatic pick counts as the week's focus when you didn't choose one (plan 3.2).
            auto_focus = FocusService().weekly(user_id, None)
            weekly = f"trait:{auto_focus['trait']}" if auto_focus else None
        return {
            "week": week_label(start + timedelta(days=1), end),
            "games": len(week),
            "feltLikeYou": sum(1 for g in week if g.get("felt_like_you") == "yes"),
            "bars": bars,
            "brilliant": {**this_week, "change": change, "trend": trend},
            "best": best,
            "lastFocus": {
                "id": weekly,
                "label": FOCUSES.get(weekly or ""),
                "line": focus_line(
                    weekly, real, cheap, survived, len(faced),
                    auto_focus or (FocusService().weekly(user_id, weekly) if (weekly or "").startswith("trait:") else None),
                ),
                "auto": auto_focus is not None,
            } if weekly else None,
            "streakWeeks": streak_weeks(kept),
            "focuses": [{"id": k, "label": v} for k, v in FOCUSES.items()],
        }

    def current_focus(self, owner_id: str, kind: str) -> str | None:
        rows = (
            get_supabase()
            .table("user_focus")
            .select("value")
            .eq("owner_id", owner_id)
            .eq("kind", kind)
            .order("set_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        return rows[0]["value"] if rows else None

    def set_focus(self, owner_id: str, kind: str, value: str) -> dict:
        allowed = FOCUSES if kind == "weekly" else INTENTS
        if value not in allowed:
            raise ValueError(f"{kind} must be one of {list(allowed)}")
        get_supabase().table("user_focus").insert(
            {"owner_id": owner_id, "kind": kind, "value": value, "set_at": datetime.now(timezone.utc).isoformat()}
        ).execute()
        return {"kind": kind, "value": value, "label": allowed[value]}
