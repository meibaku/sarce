"""
Sacrifice library (docs/DESIGN.md, screen 6): every sacrifice you played, newest first, with
what was offered, whether it held and your note. Sacrifices are a living record, never failures:
the outcome is "Held" or "Didn't hold".

What was offered is read from the position before the move: the moved piece's value minus
anything it captured ("Exchange −2" for a rook taking a minor piece, "Piece −3", "Queen −9").
"""

from __future__ import annotations

import io

import chess

from app.services.brilliant import real_offer  # noqa: F401  (re-exported for existing imports)
import chess.pgn

from app.db.supabase import get_supabase
from app.services.home import HELD
from app.services.summary import move_label

VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
CHUNK = 100


def real_sacrifice_plies(pgn_text: str, plies: list[int]) -> set[int]:
    """The subset of `plies` (0-based) that genuinely offered material in this game."""
    positions = boards_before(pgn_text)
    return {p for p in plies if p < len(positions) and real_offer(*positions[p]) > 0}


# What each tagged ply of a finished game really offered: {game_id: {ply: (kind, given) or None}}. A finished
# game's moves never change, so its PGN is parsed once per process, not on every Library/You load (the parse was
# most of a multi-second request on a large library).
_OFFERS: dict[str, dict[int, tuple[str, int] | None]] = {}


def offers_in(game_id: str, pgn_text: str, plies: list[int]) -> dict[int, tuple[str, int] | None]:
    """`offered(...)` for each of `plies` that genuinely offered material (real_offer > 0), else None; cached."""
    cached = _OFFERS.setdefault(game_id, {})
    missing = [p for p in plies if p not in cached]
    if missing:
        positions = boards_before(pgn_text)
        for p in missing:
            cached[p] = offered(*positions[p]) if p < len(positions) and real_offer(*positions[p]) > 0 else None
    return cached


def offered(board: chess.Board, move: chess.Move) -> tuple[str, int]:
    """("Exchange", 2) for Rxe5 taking a knight; ("Piece", 3) for a bishop left en prise."""
    piece = board.piece_at(move.from_square)
    if piece is None:
        return ("Sacrifice", 0)
    captured = board.piece_at(move.to_square)
    if board.is_en_passant(move):
        captured = chess.Piece(chess.PAWN, not piece.color)
    given = VALUE[piece.piece_type] - (VALUE[captured.piece_type] if captured else 0)
    given = max(given, 1)
    if piece.piece_type == chess.QUEEN:
        kind = "Queen"
    elif piece.piece_type == chess.ROOK and captured and captured.piece_type in (chess.KNIGHT, chess.BISHOP):
        kind = "Exchange"
    elif piece.piece_type == chess.PAWN:
        kind = "Pawn storm" if not captured else "Pawn"
    elif piece.piece_type == chess.ROOK:
        kind = "Rook"
    else:
        kind = "Piece"
    return (kind, given)


def boards_before(pgn_text: str) -> list[tuple[chess.Board, chess.Move]]:
    """(board before the move, move) for every ply of the mainline."""
    game = chess.pgn.read_game(io.StringIO(pgn_text or ""))
    if game is None:
        return []
    board = game.board()
    out = []
    for move in game.mainline_moves():
        out.append((board.copy(stack=False), move))
        board.push(move)
    return out


def sacrifice_glyph(move: dict, chaos_verdict: str | None) -> str:
    if move.get("is_brilliant"):
        return "!!"
    if move.get("quality") not in HELD:
        return "?"
    return "!?" if chaos_verdict == "calculated_risk" else "✓"


class LibraryService:
    def sacrifices(self, user_id: str | None, username: str | None, limit: int = 200) -> list[dict]:
        sb = get_supabase()
        q = (
            sb.table("games")
            .select("id, played_at, opponent, pgn, eco, opening")
            .eq("analysis_status", "complete")
            .neq("source", "sarce_bot")  # bot games are practice
            .order("played_at", desc=True)
            .limit(500)
        )
        if user_id:
            q = q.eq("user_id", user_id)
        if username:
            q = q.eq("chess_com_username", username)
        games = {g["id"]: g for g in q.execute().data or []}
        ids = list(games)
        moves, chaos, notes = [], {}, {}
        for start in range(0, len(ids), CHUNK):
            part = ids[start : start + CHUNK]
            moves += (
                sb.table("game_moves")
                .select("id, game_id, ply, san, uci, quality, is_brilliant, signals")
                .in_("game_id", part)
                .filter("signals", "cs", '["sacrifice"]')  # signals is jsonb
                .execute()
                .data
                or []
            )
            for n in sb.table("move_annotations").select("game_id, ply, note").in_("game_id", part).execute().data or []:
                notes[(n["game_id"], n["ply"])] = n["note"]

        # Chaos verdicts for just these moves. Asking per game returned every ply's row and hit PostgREST's
        # 1000-row cap, silently dropping verdicts (and so glyphs) for most games.
        move_ids = [m["id"] for m in moves]
        for start in range(0, len(move_ids), CHUNK):
            for r in sb.table("move_lens_scores").select("game_id, ply, verdict").in_("game_move_id", move_ids[start : start + CHUNK]).eq("lens", "chaos").execute().data or []:
                chaos[(r["game_id"], r["ply"])] = r["verdict"]

        tagged: dict[str, list[int]] = {}
        for m in moves:
            tagged.setdefault(m["game_id"], []).append(m["ply"])
        offers = {gid: offers_in(gid, games[gid].get("pgn") or "", plies) for gid, plies in tagged.items()}
        rows = []
        for m in moves:
            game = games[m["game_id"]]
            offer = offers[m["game_id"]].get(m["ply"])
            if offer is None:
                continue  # Phase 1 tagged it, but nothing was really on offer
            kind, given = offer
            held = m.get("quality") in HELD
            rows.append({
                "gameId": m["game_id"],
                "ply": m["ply"],
                "label": move_label(m["ply"], m.get("san")),
                "glyph": sacrifice_glyph(m, chaos.get((m["game_id"], m["ply"]))),
                "type": kind,
                "material": given,
                "opponent": game.get("opponent"),
                "playedAt": game.get("played_at"),
                "held": held,
                "note": notes.get((m["game_id"], m["ply"])),
                "eco": game.get("eco"),
                "opening": game.get("opening"),
            })
        rows.sort(key=lambda r: (r["playedAt"] or "", r["ply"]), reverse=True)
        return rows[:limit]
