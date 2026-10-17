"""
After-game Summary (docs/DESIGN.md, screen 3): the headline, the outcome banner, this game's
Brilliant % against the rolling window, up to three moments with the clock, and the game's one
question, "Did this game feel like you?".

"Style read" is provisional (v0) until the style schema defines it: half how close the game's
Brilliant % came to the goal's lower bound, half how much of its flagged chaos was sound.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.db.supabase import get_supabase
from app.services.home import HELD, HomeService, _count, format_time_control, is_calibrated, pick_moments, window_brilliant
from app.services.pgn_parser import mainline_positions

FELT = ("yes", "partly", "no")
STYLE_READ_VERSION = "v0"


def headline(real_problems: int, sacrifices: int, held: int) -> str:
    """Summary headline, in short sentences: "Two real problems set. One sacrifice held."."""
    parts = []
    if real_problems:
        parts.append(f"{_count(real_problems, 'real problem', 'real problems')} set.")
    if sacrifices:
        if held == sacrifices:
            parts.append(f"{_count(held, 'sacrifice', 'sacrifices')} held.")
        elif held == 0:
            parts.append(f"{_count(sacrifices, 'sacrifice', 'sacrifices')} tried.")
        else:
            parts.append(f"{held} of {sacrifices} sacrifices held.")
    if not parts:
        return "A quiet game. No real problems set."
    return " ".join(p[0].upper() + p[1:] for p in parts)


def outcome(result: str | None, moves: int, brilliant_san: str | None, moment_count: int) -> dict:
    """The banner beside the mascot: a kicker, its colour role and one sentence."""
    worth = f"{_count(moment_count, 'moment is', 'moments are')} worth a look." if moment_count else "Nothing needs a second look."
    worth = worth[0].upper() + worth[1:]
    if result == "win" and brilliant_san:
        return {"kicker": "Brilliant !!", "accent": True, "text": f"{brilliant_san} held. It goes on your timeline."}
    if result == "win":
        return {"kicker": "Won", "accent": False, "text": f"Won on move {moves}. {worth}"}
    if result == "loss":
        return {"kicker": "Lost", "accent": False, "text": f"Lost on move {moves}. {worth.replace('are worth', 'are still worth').replace('is worth', 'is still worth')}"}
    if result == "draw":
        return {"kicker": "Draw", "accent": False, "text": f"Drawn on move {moves}. Both sides kept the balance."}
    return {"kicker": "Game", "accent": False, "text": worth}


def style_read(brilliant_pct: float, goal_lo: float, real: int, calculated: int, cheap: int) -> int:
    """Provisional style read (v0), 0–100."""
    toward_goal = min(1.0, brilliant_pct / goal_lo) if goal_lo else 0.0
    flagged = real + calculated + cheap
    sound_share = (real + calculated) / flagged if flagged else 0.5
    return round(100 * (0.5 * toward_goal + 0.5 * sound_share))


def move_label(ply: int, san: str | None) -> str:
    """'19. Rxe5' / '23. …Qh4' from a 0-based ply over the whole game."""
    return f"{ply // 2 + 1}. {'…' if ply % 2 else ''}{san or ''}"


def clock_label(ms: int | None) -> str | None:
    if ms is None:
        return None
    seconds = max(0, int(ms) // 1000)
    return f"{seconds // 60}:{seconds % 60:02d}"


def lichess_analysis_url(sans: list[str]) -> str:
    """Lichess's analysis board with the moves pre-loaded (works for games from either site)."""
    tokens = []
    for i, san in enumerate(sans):
        tokens.append(f"{i // 2 + 1}.{san}" if i % 2 == 0 else san)
    return "https://lichess.org/analysis/pgn/" + "_".join(tokens)


class SummaryService:
    def summary(self, game_id: str, rolling_user_id: str | None) -> dict | None:
        sb = get_supabase()
        rows = (
            sb.table("games")
            .select("id, user_id, pgn, opponent, result, time_control, user_color, clocks_ms, chaos_data_status, felt_like_you, game_analyses(brilliant_pct, total_moves)")
            .eq("id", game_id)
            .limit(1)
            .execute()
            .data
        )
        if not rows:
            return None
        game = rows[0]
        analysis = game.pop("game_analyses", None)
        analysis = analysis[0] if isinstance(analysis, list) and analysis else (analysis or {})
        moves = sb.table("game_moves").select("ply, san, quality, is_brilliant, signals").eq("game_id", game_id).order("ply").execute().data or []
        lens_rows = sb.table("move_lens_scores").select("ply, lens, score, verdict").eq("game_id", game_id).execute().data or []
        lens_by_ply: dict[int, dict] = {}
        for row in lens_rows:
            lens_by_ply.setdefault(row["ply"], {})[row["lens"]] = row

        verdicts = [r["verdict"] for r in lens_rows if r["lens"] == "chaos"]
        real, calculated, cheap = (verdicts.count(v) for v in ("real_chaos", "calculated_risk", "cheap_chaos"))
        sacrifices = [m for m in moves if "sacrifice" in (m.get("signals") or [])]
        held = sum(1 for m in sacrifices if m.get("quality") in HELD)
        clocks = game.get("clocks_ms") or []
        moments = pick_moments(moves, lens_by_ply)
        for m in moments:
            # Plies are 0-based over the whole game; clocks_ms has one entry per ply.
            m["clock"] = clock_label(clocks[m["ply"]] if m["ply"] < len(clocks) else None)

        total = analysis.get("total_moves") or 0
        pct = float(analysis.get("brilliant_pct") or 0)
        brilliant_moves = [m for m in moves if m.get("is_brilliant")]
        goal = self._goal(game.get("user_id"))
        rolling = self._rolling(rolling_user_id or game.get("user_id"))
        # game_moves holds the user's moves only, so its length is the game's length in moves.
        full_moves = len(moves)
        first = brilliant_moves[0] if brilliant_moves else None
        first_san = move_label(first["ply"], first.get("san")) if first else None
        _, line = mainline_positions(game.get("pgn") or "")

        status = game.get("chaos_data_status")
        return {
            "gameId": game_id,
            "opponent": game.get("opponent"),
            "result": game.get("result"),
            "userColor": game.get("user_color"),
            "timeControl": format_time_control(game.get("time_control")),
            "calibrated": is_calibrated(game.get("time_control")),
            "moves": full_moves,
            "headline": headline(real, len(sacrifices), held),
            "outcome": outcome(game.get("result"), full_moves, first_san, len(moments)),
            "brilliant": {"pct": round(pct, 1), "count": len(brilliant_moves), "of": total, "rolling": rolling, **goal},
            "moments": moments,
            "analysing": status not in ("complete", "failed"),
            "felt": game.get("felt_like_you"),
            "styleRead": style_read(pct, goal["goalLo"], real, calculated, cheap),
            "styleReadVersion": STYLE_READ_VERSION,
            "lichessUrl": lichess_analysis_url([p["san"] for p in line]) if line else None,
        }

    def set_felt(self, game_id: str, answer: str) -> None:
        if answer not in FELT:
            raise ValueError(f"answer must be one of {FELT}")
        get_supabase().table("games").update({"felt_like_you": answer, "felt_at": datetime.now(timezone.utc).isoformat()}).eq("id", game_id).execute()

    def _goal(self, user_id: str | None) -> dict:
        return HomeService()._goal(user_id)

    def _rolling(self, user_id: str | None) -> float | None:
        q = (
            get_supabase()
            .table("games")
            .select("id, game_analyses(brilliant_pct, total_moves)")
            .eq("analysis_status", "complete")
            .order("played_at", desc=True)
            .limit(64)
        )
        if user_id:
            q = q.eq("user_id", user_id)
        games = []
        for row in q.execute().data or []:
            analysis = row.get("game_analyses")
            games.append({"analysis": analysis[0] if isinstance(analysis, list) and analysis else analysis})
        return window_brilliant(games)["pct"]
