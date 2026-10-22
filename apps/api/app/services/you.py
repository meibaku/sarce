"""
You (docs/DESIGN.md, screen 5): Brilliant % with its 12-week trend and formula, the style
fingerprint (6 traits × 12 weeks), your values on the reference axes, the time-control split,
the survival story and the sacrifice count.

Trait definitions (v0, shown to the player on the screen):
- Sacrifice: share of your moves that sacrifice material (Phase 1 signal).
- Chaos: share of your scored moves that set a real or speculative problem.
- Calm: share of your moves without a large evaluation swing.
- Initiative: mean chaos score of your moves (the pressure you keep on).
- Defence: share of problems set for you that you survived.
- Grip: share of your moves made while clearly winning that kept the advantage without giving the opponent air
  back (squeeze lens): converting the way Petrosian and Karpov did.

Weeks are the 12 ending at your latest analysed game, so an older history still has a picture.
Anything resting on fewer than MIN_GAMES games is None and the UI dashes it.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.db.supabase import get_supabase
from app.services.reference_axes import AXES, axis_values, references
from app.services.home import MIN_GAMES, PAGE, HomeService, format_time_control, window_brilliant
from app.services.summary import clock_label, move_label

WEEKS = 12
TRAITS = ["Sacrifice", "Chaos", "Calm", "Initiative", "Defence", "Grip"]
STEADY = 0.1  # relative change below which a trait counts as "holding steady"
CHUNK = 100  # game ids per request, to keep URLs short


def time_class(raw: str | None) -> str:
    """bullet (< 3 min), blitz (< 10 min), rapid (anything longer); daily games count as rapid."""
    if not raw or "/" in raw:
        return "rapid"
    try:
        base = int(raw.split("+")[0])
    except ValueError:
        return "rapid"
    return "bullet" if base < 180 else "blitz" if base < 600 else "rapid"


def week_index(played_at: str, end: datetime) -> int | None:
    """0 = oldest of the 12 weeks, 11 = the week ending at `end`; None outside the window."""
    when = datetime.fromisoformat(played_at.replace("Z", "+00:00"))
    weeks_back = int((end - when).total_seconds() // (7 * 86400))
    return None if weeks_back < 0 or weeks_back >= WEEKS else WEEKS - 1 - weeks_back


def trait_values(moves: list[dict], lens: list[dict]) -> dict[str, float | None]:
    """The six traits for one set of moves and lens rows (one week, or all games)."""
    n = len(moves)
    chaos = [r for r in lens if r["lens"] == "chaos"]
    faced = [r for r in lens if r["lens"] == "survival" and r["verdict"] in ("survived", "missed")]
    winning = [r for r in lens if r["lens"] == "squeeze"]
    return {
        "Sacrifice": sum("sacrifice" in (m.get("signals") or []) for m in moves) / n if n else None,
        "Chaos": sum(r["verdict"] in ("real_chaos", "calculated_risk") for r in chaos) / len(chaos) if chaos else None,
        "Calm": 1 - sum("evaluation_swing" in (m.get("signals") or []) for m in moves) / n if n else None,
        "Initiative": sum(float(r.get("score") or 0) for r in chaos) / len(chaos) if chaos else None,
        "Defence": sum(r["verdict"] == "survived" for r in faced) / len(faced) if faced else None,
        "Grip": sum(r["verdict"] != "gave_air" for r in winning) / len(winning) if winning else None,
    }


def heat_levels(row: list[float | None]) -> list[int]:
    """0–7 ramp per trait, relative to that trait's own range over the window; empty weeks are 0."""
    present = [v for v in row if v is not None]
    if not present:
        return [0] * len(row)
    lo, hi = min(present), max(present)
    span = hi - lo
    return [0 if v is None else (4 if span == 0 else 1 + round((v - lo) / span * 6)) for v in row]


def fingerprint_sentence(rows: dict[str, list[float | None]]) -> str:
    """"More sacrifice and initiative, with defence holding steady." from early vs late weeks."""
    more, less, steady = [], [], []
    for trait, row in rows.items():
        early = [v for v in row[:4] if v is not None]
        late = [v for v in row[-4:] if v is not None]
        if not early or not late:
            continue
        a, b = sum(early) / len(early), sum(late) / len(late)
        change = (b - a) / a if a else (1.0 if b else 0.0)
        (more if change > STEADY else less if change < -STEADY else steady).append(trait.lower())
    if not (more or less or steady):
        return "Not enough weeks with analysed games to compare yet."
    parts = []
    if more:
        parts.append("More " + " and ".join(more))
    if less:
        parts.append(("less " if parts else "Less ") + " and ".join(less))
    sentence = ", ".join(parts)
    if steady:
        holds = " and ".join(steady) + " holding steady"
        sentence = f"{sentence}, with {holds}" if sentence else holds[0].upper() + holds[1:]
    return sentence + "."


DETAIL_KEYS = ("faced_chaos", "elo", "p_fail")
LENS_COLUMNS = "game_id, ply, lens, score, verdict, " + ", ".join(f"{k}:details->{k}" for k in DETAIL_KEYS)


class YouService:
    def you(self, user_id: str | None, username: str | None) -> dict:
        sb = get_supabase()

        def scoped(q):
            if user_id:
                q = q.eq("user_id", user_id)
            if username:
                q = q.eq("chess_com_username", username)
            return q

        games = scoped(
            sb.table("games")
            .select("id, played_at, opponent, time_control, clocks_ms, game_analyses(brilliant_pct, total_moves, style_vector)")
            .eq("analysis_status", "complete")
            .neq("source", "sarce_bot")  # bot games are practice
            .order("played_at", desc=True)
            .limit(500)
        ).execute().data or []
        for g in games:
            a = g.pop("game_analyses", None)
            g["analysis"] = a[0] if isinstance(a, list) and a else a
        goal = HomeService()._goal(user_id)
        if not games:
            return {"games": 0, **goal, "brilliant": None, "fingerprint": None, "axes": None, "timeControls": [], "survival": None, "sacrifices": None}

        ids = [g["id"] for g in games]
        moves, lens = [], []
        for start in range(0, len(ids), CHUNK):
            part = ids[start : start + CHUNK]
            moves += self._paged(lambda: sb.table("game_moves").select("game_id, ply, san, quality, signals, is_brilliant").in_("game_id", part).order("id"))
            lens += self._paged(
                lambda: sb.table("move_lens_scores").select(LENS_COLUMNS).in_("game_id", part).in_("lens", ["chaos", "survival", "squeeze"]).order("game_move_id")
            )
        for r in lens:
            # Only three keys of `details` are read; selecting them alone keeps the blob off the wire.
            if "details" not in r:
                r["details"] = {k: r.pop(k, None) for k in DETAIL_KEYS}

        by_game_moves: dict[str, list[dict]] = {}
        for m in moves:
            by_game_moves.setdefault(m["game_id"], []).append(m)
        by_game_lens: dict[str, list[dict]] = {}
        for r in lens:
            by_game_lens.setdefault(r["game_id"], []).append(r)

        end = datetime.fromisoformat(games[0]["played_at"].replace("Z", "+00:00")) + timedelta(seconds=1)
        weekly_moves: list[list[dict]] = [[] for _ in range(WEEKS)]
        weekly_lens: list[list[dict]] = [[] for _ in range(WEEKS)]
        weekly_games: list[list[dict]] = [[] for _ in range(WEEKS)]
        for g in games:
            w = week_index(g["played_at"], end) if g.get("played_at") else None
            if w is None:
                continue
            weekly_games[w].append(g)
            weekly_moves[w].extend(by_game_moves.get(g["id"], []))
            weekly_lens[w].extend(by_game_lens.get(g["id"], []))

        weekly_traits = [trait_values(weekly_moves[w], weekly_lens[w]) for w in range(WEEKS)]
        rows = {t: [weekly_traits[w][t] for w in range(WEEKS)] for t in TRAITS}
        overall = trait_values(moves, lens)
        enough = len(games) >= MIN_GAMES

        all_brilliant = window_brilliant(games)
        weekly_pct = [window_brilliant(weekly_games[w])["pct"] if len(weekly_games[w]) else None for w in range(WEEKS)]
        brilliant_moves = sum(1 for m in moves if m.get("is_brilliant"))
        first_pct = next((p for p in weekly_pct if p is not None), None)
        # The first week scored under the find-rate rule (ADR 0004), for the trend's "style v2" marker.
        def version(g: dict) -> int:
            return int(((g.get("analysis") or {}).get("style_vector") or {}).get("version") or 1)

        # Version 2 added the find-rate rule (ADR 0004), version 3 the real-offer rule (ADR 0007).
        v2_weeks = [w for w in range(WEEKS) if any(version(g) >= 2 for g in weekly_games[w])]
        schema = max((version(g) for g in games), default=1)

        mine, refs = axis_values(overall), references()
        return {
            "games": len(games),
            **goal,
            "brilliant": {
                "pct": all_brilliant["pct"],
                "spread": all_brilliant["spread"],
                "weekly": weekly_pct,
                "from": first_pct if enough else None,
                "brilliantMoves": brilliant_moves,
                "yourMoves": len(moves),
                "ruleChangedWeek": v2_weeks[0] if v2_weeks and v2_weeks[0] > 0 else None,
                "findRateRule": schema >= 2,
            },
            "styleSchema": schema,
            "fingerprint": {
                "traits": TRAITS,
                "levels": [heat_levels(rows[t]) for t in TRAITS],
                "sentence": fingerprint_sentence(rows) if enough else "Fills in after five analysed games.",
            },
            "axes": [
                {
                    "name": name,
                    "you": mine[name] if enough else None,
                    "refs": {player: ref["axes"].get(name) for player, ref in refs.items()},
                }
                for name in AXES
            ],
            "references": {player: {"games": ref.get("games", 0), "model": ref.get("model")} for player, ref in refs.items()},
            "timeControls": self._time_controls(games),
            "survival": self._survival(games, by_game_lens, by_game_moves, end, overall["Defence"], enough),
            "grip": self._grip(games, by_game_lens, by_game_moves),
            "sacrifices": self._sacrifices(user_id, username),
        }

    @staticmethod
    def _grip(games: list[dict], by_game_lens: dict, by_game_moves: dict) -> dict | None:
        """Converting advantages (squeeze lens): how often a winning position stayed tight, and the latest leak."""
        rows = [r for g in games for r in by_game_lens.get(g["id"], []) if r["lens"] == "squeeze"]
        if not rows:
            return None
        leak = None
        for g in games:  # newest first
            r = next((r for r in sorted(by_game_lens.get(g["id"], []), key=lambda r: -r["ply"]) if r["lens"] == "squeeze" and r["verdict"] == "gave_air"), None)
            if r:
                san = next((m.get("san") for m in by_game_moves.get(g["id"], []) if m["ply"] == r["ply"]), None)
                leak = {"gameId": g["id"], "ply": r["ply"], "label": move_label(r["ply"], san), "opponent": g.get("opponent")}
                break
        return {
            "moves": len(rows),
            "squeezed": sum(r["verdict"] == "squeezed" for r in rows),
            "gaveAir": sum(r["verdict"] == "gave_air" for r in rows),
            "latestLeak": leak,
        }

    @staticmethod
    def _sacrifices(user_id: str | None, username: str | None) -> dict:
        """Same genuine-offer rule as the library, so the two screens agree."""
        from app.services.library import LibraryService

        rows = LibraryService().sacrifices(user_id, username, limit=10_000)
        return {"played": len(rows), "held": sum(r["held"] for r in rows), "withNotes": sum(1 for r in rows if r["note"])}

    @staticmethod
    def _paged(build) -> list[dict]:
        rows: list[dict] = []
        while True:
            batch = build().range(len(rows), len(rows) + PAGE - 1).execute().data or []
            rows.extend(batch)
            if len(batch) < PAGE:
                return rows

    @staticmethod
    def _time_controls(games: list[dict]) -> list[dict]:
        out = []
        for cls in ("bullet", "blitz", "rapid"):
            subset = [g for g in games if time_class(g.get("time_control")) == cls]
            card = window_brilliant(subset)
            out.append({"class": cls, "games": len(subset), "pct": card["pct"], "spread": card["spread"], "calibrated": cls == "bullet"})
        return out

    @staticmethod
    def _survival(games, by_game_lens, by_game_moves, end, defence, enough) -> dict | None:
        week_ago = end - timedelta(days=7)
        recent = {g["id"]: g for g in games if g.get("played_at") and datetime.fromisoformat(g["played_at"].replace("Z", "+00:00")) >= week_ago}
        if not recent:
            recent = {games[0]["id"]: games[0]}
        best = None
        for gid, g in recent.items():
            for r in by_game_lens.get(gid, []):
                if r["lens"] != "survival" or r["verdict"] not in ("survived", "missed"):
                    continue
                faced = float((r.get("details") or {}).get("faced_chaos") or r.get("score") or 0)
                if best is None or faced > best[0]:
                    best = (faced, g, r)
        if best is None:
            return None
        _, g, r = best
        details = r.get("details") or {}
        elo = str(details.get("elo") or "")
        p_fail = (details.get("p_fail") or {}).get(elo)
        reply = next((m.get("san") for m in by_game_moves.get(g["id"], []) if m["ply"] == r["ply"]), None)
        clocks = g.get("clocks_ms") or []
        return {
            "gameId": g["id"],
            "ply": r["ply"],
            "opponent": g.get("opponent"),
            "moveNumber": r["ply"] // 2 + 1,
            "survived": r["verdict"] == "survived",
            "reply": reply,
            "pFail": None if p_fail is None else round(float(p_fail), 2),
            "clock": clock_label(clocks[r["ply"]] if r["ply"] < len(clocks) else None),
            "timeControl": format_time_control(g.get("time_control")),
            "trapsSurvived": None if not enough or defence is None else round(defence, 2),
        }
