from datetime import datetime, timezone


def _parse_result(white_result: str, user_color: str) -> str:
    if white_result in ("win", "resigned", "timeout", "abandoned"):
        return "win" if user_color == "white" else "loss"
    if white_result in ("checkmated", "insufficient", "stalemate", "agreed", "repetition", "50move", "timevsinsufficient"):
        return "loss" if user_color == "white" else "win"
    return "draw"


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
        "result": _parse_result(white.get("result", ""), user_color),
        "user_color": user_color,
    }
