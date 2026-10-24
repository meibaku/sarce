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
from app.services.budget import chaos_budget
from app.services.distraction import flagged_plies
from app.services.home import HELD, HomeService, _count, format_time_control, is_calibrated, pick_moments, window_brilliant
from app.services.pgn_parser import mainline_positions
from app.services.questions import CHECKIN_ANSWERS, checkin_target, grade_intention, intention_for, rotation

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
    def summary(self, game_id: str, rolling_user_id: str | None, owner_id: str | None = None) -> dict | None:
        sb = get_supabase()
        rows = (
            sb.table("games")
            .select("id, user_id, pgn, played_at, opponent, result, time_control, user_color, clocks_ms, chaos_data_status, felt_like_you, game_analyses(brilliant_pct, total_moves)")
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
        lens_rows = (
            sb.table("move_lens_scores").select("ply, lens, score, verdict, objective_cost:details->objective_cost, reply_ep_loss:details->reply_ep_loss")
            .eq("game_id", game_id).execute().data
            or []
        )
        for row in lens_rows:
            row["details"] = {"objective_cost": row.pop("objective_cost", None), "reply_ep_loss": row.pop("reply_ep_loss", None)}
        lens_by_ply: dict[int, dict] = {}
        for row in lens_rows:
            lens_by_ply.setdefault(row["ply"], {})[row["lens"]] = row

        verdicts = [r["verdict"] for r in lens_rows if r["lens"] == "chaos"]
        real, calculated, cheap = (verdicts.count(v) for v in ("real_chaos", "calculated_risk", "cheap_chaos"))
        from app.services.library import real_sacrifice_plies

        offered = real_sacrifice_plies(game.get("pgn") or "", [m["ply"] for m in moves if "sacrifice" in (m.get("signals") or [])])
        sacrifices = [m for m in moves if m["ply"] in offered]
        held = sum(1 for m in sacrifices if m.get("quality") in HELD)
        clocks = game.get("clocks_ms") or []
        moments = pick_moments(moves, lens_by_ply, checkin=flagged_plies(game, moves, lens_rows))
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
            **self._questions(game, moves, lens_rows, sacrifices, moments, owner_id),
            "lichessUrl": lichess_analysis_url([p["san"] for p in line]) if line else None,
            "budget": chaos_budget(lens_rows),
        }

    def _questions(self, game: dict, moves: list[dict], lens_rows: list[dict], sacrifices: list[dict], moments: list[dict], owner_id: str | None) -> dict:
        """This game's questions (rotation within the budget) and how today's intention went."""
        from app.services.review import ask_for
        from app.services.settings_store import SettingsStore

        sb = get_supabase()
        owner = owner_id or game.get("user_id")
        budget = SettingsStore().get(owner)["questionBudget"] if owner else 1
        notes = {n["ply"] for n in sb.table("move_annotations").select("ply").eq("game_id", game["id"]).execute().data or []}
        answers = {a["ply"]: a["answer"] for a in sb.table("game_answers").select("ply, answer").eq("game_id", game["id"]).eq("kind", "checkin").execute().data or []}
        questions = []
        for kind in rotation(game["id"], budget):
            if kind == "felt":
                questions.append({"kind": "felt", "answer": game.get("felt_like_you")})
            elif kind == "intent":
                asked = [m for m in moments if m["glyph"] != "?!"]  # a check-in moment gets the check-in question
                target = next((m for m in asked if m["ply"] not in notes), asked[0] if asked else None)
                if target:
                    questions.append({"kind": "intent", "ply": target["ply"], "label": move_label(target["ply"], target.get("san")), "ask": ask_for(target["glyph"], "set", False), "answered": target["ply"] in notes})
            else:
                ply, flagged = checkin_target(game["id"], flagged_plies(game, moves, lens_rows), [m["ply"] for m in moves])
                if ply is not None:
                    san = next((m.get("san") for m in moves if m["ply"] == ply), None)
                    questions.append({"kind": "checkin", "ply": ply, "label": move_label(ply, san), "flagged": flagged, "answer": answers.get(ply)})

        intents = sb.table("user_focus").select("value, set_at").eq("owner_id", owner).eq("kind", "today").execute().data or [] if owner else []
        survival = [r["verdict"] for r in lens_rows if r["lens"] == "survival"]
        intention = grade_intention(
            intention_for(intents, game.get("played_at")),
            [move_label(m["ply"], m.get("san")) for m in sacrifices],
            survival.count("survived"),
            survival.count("missed"),
            sum(1 for r in lens_rows if r["lens"] == "chaos" and r["verdict"] == "cheap_chaos"),
            sum(1 for m in moves if m.get("quality") in ("mistake", "blunder", "miss")),
        )
        return {"questions": questions, "intention": intention}

    def set_checkin(self, game_id: str, ply: int, answer: str, flagged: bool) -> None:
        if answer not in CHECKIN_ANSWERS:
            raise ValueError(f"answer must be one of {CHECKIN_ANSWERS}")
        get_supabase().table("game_answers").upsert(
            {"game_id": game_id, "kind": "checkin", "ply": ply, "answer": answer, "flagged": flagged}, on_conflict="game_id,kind,ply"
        ).execute()

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
