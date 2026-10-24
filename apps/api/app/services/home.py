"""
Home screen data (docs/DESIGN.md, screen 2): the latest game's style read, chaos strip and
moments, and the Brilliant card for the recent window.

Pure helpers come first so the wording and the honesty rules are testable without a database:
a metric resting on fewer than MIN_GAMES games is returned as None (the UI dashes it), and
sacrifices and chaos are never described as failures.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from app.db.supabase import get_supabase
from app.services.uncertainty import ROLLING_GAMES, ROLLING_POINTS, ROLLING_STEP, wilson
from app.services.distraction import flagged_plies

WINDOW = 64
MIN_GAMES = 5
MAX_MOMENTS = 3
PAGE = 1000

# A sacrifice "held" when the engine classed it at good or better.
HELD = {"brilliant", "best", "excellent", "good"}


def format_time_control(raw: str | None) -> str | None:
    """'60' -> '1+0', '180+2' -> '3+2', '1/259200' -> 'daily'."""
    if not raw:
        return None
    if "/" in raw:
        return "daily"
    base, _, inc = raw.partition("+")
    try:
        minutes = int(base) / 60
    except ValueError:
        return raw
    shown = str(int(minutes)) if minutes.is_integer() else f"{minutes:g}"
    return f"{shown}+{inc or 0}"


def is_calibrated(raw: str | None) -> bool:
    """Chaos numbers are validated on one-minute games without increment only (docs/VALIDATION.md)."""
    return raw in ("60", "60+0")


def _count(n: int, one: str, many: str) -> str:
    words = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    return f"{words[n] if n < len(words) else n} {one if n == 1 else many}"


def style_read(real_problems: int, sacrifices: int, held: int) -> str:
    """The one-sentence read of a game that leads Home. Mirrors, never grades."""
    if real_problems == 0 and sacrifices == 0:
        return "A quiet game: no real problems set and no sacrifices."
    parts = []
    if real_problems:
        parts.append(f"You set {_count(real_problems, 'real problem', 'real problems')}")
    if sacrifices:
        if held == sacrifices:
            tail = f"{_count(sacrifices, 'sacrifice', 'sacrifices')} held" if sacrifices > 1 else "one sacrifice held"
        elif held == 0:
            tail = f"you tried {_count(sacrifices, 'sacrifice', 'sacrifices')}"
        else:
            tail = f"{held} of {sacrifices} sacrifices held"
        parts.append(tail if parts else tail[0].upper() + tail[1:])
    return (", and ".join(parts) if len(parts) > 1 else parts[0]) + "."


def moment_glyph(move: dict, lenses: dict) -> str | None:
    """Badge for a move worth showing (docs/DESIGN.md copy mapping); None when it isn't a moment."""
    chaos = (lenses.get("chaos") or {}).get("verdict")
    survival = (lenses.get("survival") or {}).get("verdict")
    if move.get("is_brilliant"):
        return "!!"
    if survival == "missed" or chaos == "cheap_chaos":
        return "?"
    if chaos == "real_chaos" or survival == "survived":
        return "✓"
    if chaos == "calculated_risk":
        return "!?"
    return None


def moment_line(glyph: str, move: dict, lenses: dict) -> str:
    chaos = (lenses.get("chaos") or {}).get("verdict")
    survival = (lenses.get("survival") or {}).get("verdict")
    sacrifice = "sacrifice" in (move.get("signals") or [])
    if glyph == "!!":
        return "The sacrifice held" if sacrifice else "A brilliant move"
    if survival == "survived":
        return "Trap faced, safe reply found"
    if survival == "missed":
        return "Trap faced, didn't hold"
    if chaos == "real_chaos":
        return "You set a real problem"
    if chaos == "cheap_chaos":
        return "Unsound chaos"
    return "A speculative try"


CHECKIN_LINE = "Your pace changed here"


def pick_moments(moves: list[dict], lens_by_ply: dict[int, dict], limit: int = MAX_MOMENTS, checkin: list[int] | None = None) -> list[dict]:
    """
    Up to `limit` moments (three on Home and Summary), the strongest by chaos score, in game order.
    `checkin` are distraction-flagged plies (services/distraction.py), strongest first: the top one
    always gets a slot, as a ?! check-in unless it is already a moment.
    """
    found = []
    for move in moves:
        lenses = lens_by_ply.get(move["ply"], {})
        glyph = moment_glyph(move, lenses)
        if glyph is None:
            continue
        weight = max(float((lenses.get(k) or {}).get("score") or 0) for k in ("chaos", "survival"))
        weight += 1.0 if glyph == "!!" else 0.0
        found.append((weight, move, glyph, lenses))
    found.sort(key=lambda item: -item[0])
    chosen = found[:limit]
    by_ply = {m["ply"]: m for m in moves}
    flagged = next((p for p in (checkin or []) if p in by_ply), None)
    if flagged is not None and limit > 0 and all(item[1]["ply"] != flagged for item in chosen):
        chosen = chosen[: limit - 1] + [(0.0, by_ply[flagged], "?!", {})]
    chosen.sort(key=lambda item: item[1]["ply"])
    return [
        {
            "ply": move["ply"],
            "san": move.get("san"),
            "glyph": glyph,
            "line": CHECKIN_LINE if glyph == "?!" else moment_line(glyph, move, lenses),
        }
        for _, move, glyph, lenses in chosen
    ]


def window_brilliant(games: list[dict]) -> dict:
    """Brilliant % over the window with its Wilson 95% interval (lo/hi, review F4), standard error and games."""
    moves = brilliant = 0.0
    counted = 0
    for game in games:
        analysis = game.get("analysis") or {}
        total = analysis.get("total_moves") or 0
        if not total:
            continue
        counted += 1
        moves += total
        brilliant += float(analysis.get("brilliant_pct") or 0) * total / 100
    if counted < MIN_GAMES or moves == 0:
        return {"pct": None, "spread": None, "lo": None, "hi": None, "games": counted, "moves": int(moves)}
    p = brilliant / moves
    lo, hi = wilson(brilliant, moves)
    return {
        "pct": round(p * 100, 2),
        "spread": round(math.sqrt(p * (1 - p) / moves) * 100, 2),
        "lo": round(lo * 100, 2),
        "hi": round(hi * 100, 2),
        "games": counted,
        "moves": int(moves),
    }


def rolling_brilliant(games_newest_first: list[dict]) -> list[dict]:
    """
    Brilliant % over rolling windows of ROLLING_GAMES games (step ROLLING_STEP), oldest first, each with its interval:
    the trend the You screen draws instead of one noisy point per game or week (review F4).
    """
    games = [g for g in reversed(games_newest_first) if (g.get("analysis") or {}).get("total_moves")]
    points = []
    for end in range(len(games), ROLLING_GAMES - 1, -ROLLING_STEP):
        window = games[end - ROLLING_GAMES : end]
        w = window_brilliant(window)
        if w["pct"] is not None:
            points.append({"pct": w["pct"], "lo": w["lo"], "hi": w["hi"], "games": w["games"], "endAt": window[-1].get("played_at")})
        if len(points) >= ROLLING_POINTS:
            break
    return points[::-1]


def next_band(hi: float | None, goal_lo: float) -> tuple[float, float] | None:
    """
    A personal next step on the way to the goal band (plan 1.3): from just above the top of your likely range (its
    95% upper bound, rounded up to 0.1) to half as much again, at least half a point wide, capped at the goal.
    None when there's no range yet or you are within half a point of the goal band.
    """
    if hi is None:
        return None
    lo = max(0.1, math.ceil(round(hi * 10, 6)) / 10)
    if goal_lo - lo < 0.5:  # less than half a point short: the next step is the goal band itself
        return None
    return lo, min(goal_lo, round(lo + max(0.5, lo / 2), 1))  # round first: the cap must hold for fractional goals


def gap_line(pct: float | None, lo: float, hi: float) -> str:
    if pct is None:
        return f"Your {lo:g}–{hi:g}% band fills in after {MIN_GAMES} analysed games."
    if pct < lo:
        return f"{lo - pct:.1f} points below your {lo:g}–{hi:g}% band."
    if pct > hi:
        return f"{pct - hi:.1f} points above your {lo:g}–{hi:g}% band."
    return f"Inside your {lo:g}–{hi:g}% band."


SESSION_MAX = 1000  # games read for the session line; a longer absence is summarised over the newest 1,000


def parse_since(since: str | None) -> datetime | None:
    if not since:
        return None
    try:
        cutoff = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError:
        return None
    return cutoff if cutoff.tzinfo else cutoff.replace(tzinfo=timezone.utc)


def summarise_session(games: list[dict], real_by_game: dict[str, int]) -> dict | None:
    """The session line's numbers for the games analysed since your last visit; None when there are none."""
    if not games:
        return None
    return {
        "games": len(games),
        "feltLikeYou": sum(1 for g in games if g.get("felt_like_you") == "yes"),
        "realProblems": sum(real_by_game.get(g["id"], 0) for g in games),
        "brilliant": sum(1 for g in games if float((g.get("analysis") or {}).get("brilliant_pct") or 0) > 0),
    }


def style_streak(games_newest_first: list[dict], real_by_game: dict[str, int]) -> int:
    """Games in a row, newest first, with at least one real problem or brilliant move."""
    streak = 0
    for game in games_newest_first:
        brilliant = float((game.get("analysis") or {}).get("brilliant_pct") or 0) > 0
        if real_by_game.get(game["id"], 0) > 0 or brilliant:
            streak += 1
        else:
            break
    return streak


def _paged(build) -> list[dict]:
    rows: list[dict] = []
    while True:
        batch = build().range(len(rows), len(rows) + PAGE - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < PAGE:
            return rows


class HomeService:
    """Loads Home for one user (and optionally one Chess.com username)."""

    def home(self, user_id: str | None, username: str | None, since: str | None = None) -> dict:
        sb = get_supabase()

        def games_query():
            q = (
                sb.table("games")
                .select("id, played_at, opponent, result, time_control, user_color, clocks_ms, game_analyses(brilliant_pct, total_moves)")
                .eq("analysis_status", "complete")
                .neq("source", "sarce_bot")  # bot games are practice
                .order("played_at", desc=True)
                .limit(WINDOW)
            )
            if user_id:
                q = q.eq("user_id", user_id)
            if username:
                q = q.eq("chess_com_username", username)
            return q

        games = games_query().execute().data or []
        for game in games:
            analysis = game.pop("game_analyses", None)
            game["analysis"] = analysis[0] if isinstance(analysis, list) and analysis else analysis
        goal = self._goal(user_id)
        if not games:
            return {"latest": None, "brilliant": {**window_brilliant([]), **goal}, "stats": None}

        ids = [g["id"] for g in games]
        lens_rows = _paged(
            lambda: sb.table("move_lens_scores")
            .select("game_id, ply, lens, score, verdict")
            .in_("game_id", ids)
            .in_("lens", ["chaos", "survival"])
            .order("game_move_id")
        )
        real_by_game: dict[str, int] = {}
        cheap = real = survived = faced = 0
        for row in lens_rows:
            if row["lens"] == "chaos":
                real += row["verdict"] == "real_chaos"
                cheap += row["verdict"] == "cheap_chaos"
                if row["verdict"] == "real_chaos":
                    real_by_game[row["game_id"]] = real_by_game.get(row["game_id"], 0) + 1
            elif row["verdict"] in ("survived", "missed"):
                faced += 1
                survived += row["verdict"] == "survived"

        latest = games[0]
        enough = len(games) >= MIN_GAMES
        brilliant = {**window_brilliant(games), **goal}
        brilliant["gapLine"] = gap_line(brilliant["pct"], goal["goalLo"], goal["goalHi"])
        step = next_band(brilliant.get("hi"), goal["goalLo"])
        brilliant["nextLo"], brilliant["nextHi"] = step if step else (None, None)
        return {
            "latest": self._latest(latest, [r for r in lens_rows if r["game_id"] == latest["id"]]),
            "brilliant": brilliant,
            "session": self._session(user_id, username, since),
            "stats": {
                "streak": style_streak(games, real_by_game) if enough else None,
                "real": real,
                "cheap": cheap,
                "soundRatio": round(real / cheap, 1) if enough and cheap else None,
                "trapsSurvived": round(survived / faced, 2) if enough and faced else None,
            },
        }

    def _session(self, user_id: str | None, username: str | None, since: str | None) -> dict | None:
        """
        The games whose analysis finished after `since` (plan 3.4a), read on their own: by analysis time, so a game
        played earlier but analysed after your visit still counts, and not limited to Home's rolling window.
        """
        cutoff = parse_since(since)
        if cutoff is None:
            return None
        sb = get_supabase()
        q = (
            sb.table("games").select("id, felt_like_you, game_analyses(brilliant_pct)")
            .eq("analysis_status", "complete").neq("source", "sarce_bot").gt("analysed_at", cutoff.isoformat())
            .order("analysed_at", desc=True).limit(SESSION_MAX)
        )
        if user_id:
            q = q.eq("user_id", user_id)
        if username:
            q = q.eq("chess_com_username", username)
        games = q.execute().data or []
        for g in games:
            a = g.pop("game_analyses", None)
            g["analysis"] = a[0] if isinstance(a, list) and a else a
        real: dict[str, int] = {}
        ids = [g["id"] for g in games]
        for start in range(0, len(ids), 100):
            rows = _paged(
                lambda: sb.table("move_lens_scores").select("game_id").in_("game_id", ids[start : start + 100])
                .eq("lens", "chaos").eq("verdict", "real_chaos").order("game_move_id")
            )
            for r in rows:
                real[r["game_id"]] = real.get(r["game_id"], 0) + 1
        return summarise_session(games, real)

    def _goal(self, user_id: str | None) -> dict:
        lo, hi = 6, 10
        if user_id:
            res = get_supabase().table("profiles").select("style_goal").eq("id", user_id).limit(1).execute()
            goal = (res.data[0].get("style_goal") if res.data else None) or {}
            lo = goal.get("target_brilliant_min", lo)
            hi = goal.get("target_brilliant_max", hi)
        return {"goalLo": lo, "goalHi": hi}

    def _latest(self, game: dict, lens_rows: list[dict]) -> dict:
        from app.services.library import real_sacrifice_plies

        moves = (
            get_supabase()
            .table("game_moves")
            .select("ply, san, quality, is_brilliant, signals")
            .eq("game_id", game["id"])
            .order("ply")
            .execute()
            .data
            or []
        )
        lens_by_ply: dict[int, dict] = {}
        for row in lens_rows:
            lens_by_ply.setdefault(row["ply"], {})[row["lens"]] = row
        user_plies = sorted({row["ply"] for row in lens_rows if row["lens"] == "chaos"})
        chaos = [float((lens_by_ply[p].get("chaos") or {}).get("score") or 0) for p in user_plies]
        brilliant_ply = next((m["ply"] for m in moves if m.get("is_brilliant")), None)
        pgn = (get_supabase().table("games").select("pgn").eq("id", game["id"]).limit(1).execute().data or [{}])[0].get("pgn") or ""
        tagged = [m["ply"] for m in moves if "sacrifice" in (m.get("signals") or [])]
        offered = real_sacrifice_plies(pgn, tagged)
        sacrifices = [m for m in moves if m["ply"] in offered]
        real = sum(1 for p in user_plies if (lens_by_ply[p].get("chaos") or {}).get("verdict") == "real_chaos")
        return {
            "gameId": game["id"],
            "playedAt": game.get("played_at"),
            "opponent": game.get("opponent"),
            "result": game.get("result"),
            "userColor": game.get("user_color"),
            "timeControl": format_time_control(game.get("time_control")),
            "calibrated": is_calibrated(game.get("time_control")),
            "styleRead": style_read(real, len(sacrifices), sum(1 for m in sacrifices if m.get("quality") in HELD)),
            "chaos": chaos,
            "highlight": user_plies.index(brilliant_ply) if brilliant_ply in user_plies else None,
            "moments": pick_moments(moves, lens_by_ply, checkin=flagged_plies(game, moves, lens_rows)),
        }
