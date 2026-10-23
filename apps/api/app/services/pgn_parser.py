from datetime import datetime, timezone
import io
import re

import chess
import chess.pgn


# Chess.com's per-player `result` is that player's own outcome: "win", a draw code, or how they lost.
DRAW_CODES = {"agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient"}
LOSS_CODES = {"checkmated", "resigned", "timeout", "abandoned", "lose", "kingofthehill", "threecheck", "bughousepartnerlose"}
PGN_RESULTS = {"1-0": "white", "0-1": "black", "1/2-1/2": "draw"}


def _pgn_result(pgn: str) -> str | None:
    """The PGN's own [Result] header: "white", "black", "draw", or None when absent or "*"."""
    match = re.search(r'\[Result "([^"]+)"\]', pgn or "")
    return PGN_RESULTS.get(match.group(1)) if match else None


def _parse_result(white_result: str, user_color: str, pgn: str = "") -> str:
    """
    The user's result. The PGN's [Result] header is the source of truth; Chess.com's codes are the fallback.

    An earlier version read White's code as if "resigned"/"timeout"/"abandoned" meant White *won* and every draw code
    meant White lost, which inverted about a third of results (fixed in migration 20261023000000).
    """
    winner = _pgn_result(pgn)
    if winner is None:
        if white_result == "win":
            winner = "white"
        elif white_result in DRAW_CODES:
            winner = "draw"
        elif white_result in LOSS_CODES:
            winner = "black"
        else:
            return "draw"
    if winner == "draw":
        return "draw"
    return "win" if winner == user_color else "loss"


def parse_chess_com_game(raw: dict, username: str) -> dict | None:
    pgn = raw.get("pgn")
    if not pgn:
        return None

    white = raw.get("white", {})
    black = raw.get("black", {})
    user_color = "white" if white.get("username", "").lower() == username.lower() else "black"
    opponent_data = black if user_color == "white" else white

    played_at = None
    if ts := raw.get("end_time"):
        played_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    external_id = raw.get("url") or raw.get("uuid") or f"{username}-{played_at}"

    return {
        "external_id": external_id,
        "pgn": pgn,
        "played_at": played_at,
        "opponent": opponent_data.get("username", "unknown"),
        "opponent_rating": opponent_data.get("rating"),
        "time_control": raw.get("time_control"),
        "result": _parse_result(white.get("result", ""), user_color, pgn),
        "user_color": user_color,
    }


def mainline_positions(pgn_text: str) -> tuple[str, list[dict]]:
    """Return initial FEN and all mainline positions after each ply."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return chess.Board().fen(), []
    board = game.board()
    initial_fen = board.fen()
    line = []
    for ply, move in enumerate(game.mainline_moves()):
        san = board.san(move)
        board.push(move)
        line.append(
            {
                "ply": ply,
                "uci": move.uci(),
                "san": san,
                "fen": board.fen(),
            }
        )
    return initial_fen, line


def extract_clocks_ms(pgn_text: str) -> list[int | None]:
    """
    Remaining clock per ply (both players) from `[%clk ...]` comments, in milliseconds.

    Each value is the mover's time *after* that move; None where the PGN has no clock.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return []
    clocks: list[int | None] = []
    for node in game.mainline():
        seconds = node.clock()
        clocks.append(None if seconds is None else round(seconds * 1000))
    return clocks


_ECO = re.compile(r'\[ECO "([A-E][0-9]{2})"\]')
_OPENING = re.compile(r'\[Opening "([^"]+)"\]')
_ECO_URL = re.compile(r'\[ECOUrl "[^"]*/openings/([^"]+)"\]')


def opening_from_pgn(pgn_text: str | None) -> tuple[str | None, str | None]:
    """
    (ECO code, opening name) from PGN headers: Lichess's [Opening], or the name part of Chess.com's
    [ECOUrl] slug ("Caro-Kann-Defense-Exchange-Variation-3...cxd5" → "Caro Kann Defense Exchange
    Variation"). Same rule as the game_openings migration's backfill.
    """
    if not pgn_text:
        return None, None
    eco = _ECO.search(pgn_text)
    name = _OPENING.search(pgn_text)
    opening = name.group(1) if name else None
    if opening is None and (url := _ECO_URL.search(pgn_text)):
        opening = re.sub(r"-[0-9].*$", "", url.group(1)).replace("-", " ") or None
    return (eco.group(1) if eco else None), opening
