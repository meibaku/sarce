"""
Opt-in AI help for positions from videos (PHASES 2.2 and 2.4), through the Claude API.

- `fen_from_image`: reads a board from a screenshot and returns a FEN, checked by python-chess.
- `summarize_excerpt`: turns what a commentator said around a moment into short annotations.

Both send data to Anthropic, so they run only when the server has Claude credentials (the SDK reads
ANTHROPIC_API_KEY or an `ant auth login` profile) **and** the player turned on Settings → "Video help
(sent to AI)" (`aiHelp`). The engine stays the judge of the position; the AI only reads and summarises.
"""

from __future__ import annotations

import base64
import json
import os

import chess

MODEL = "claude-opus-5-5"
# Server-side refusal fallback, routed by category (no model list to maintain).
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MEDIA_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


class AIUnavailable(Exception):
    """AI help is off (no credentials on the server, or the player hasn't opted in)."""


def credentials_present() -> bool:
    """True when the SDK can authenticate: an API key / token in the environment or a CLI profile."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    home = os.path.expanduser("~")
    return os.path.isdir(os.path.join(home, ".config", "anthropic"))


def _client():
    import anthropic

    return anthropic.Anthropic()


def _json_response(content: list, schema: dict, max_tokens: int = 4000) -> dict:
    """One structured-output request; returns the parsed JSON or raises ValueError on a refusal."""
    response = _client().beta.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": content}],
    )
    if response.stop_reason == "refusal":
        raise ValueError("The request was declined.")
    text = next((b.text for b in response.content if b.type == "text"), "")
    return json.loads(text)


FEN_SCHEMA = {
    "type": "object",
    "properties": {
        "placement": {"type": "string", "description": "FEN piece placement, rank 8 to rank 1"},
        "side_to_move": {"type": "string", "enum": ["w", "b"]},
        "flipped": {"type": "boolean", "description": "true if the board is shown from Black's side"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "notes": {"type": "string"},
    },
    "required": ["placement", "side_to_move", "flipped", "confidence", "notes"],
    "additionalProperties": False,
}

FEN_PROMPT = (
    "This is a screenshot of a chess position, possibly from a video. Read the board square by square "
    "and give the piece placement as standard FEN (rank 8 first, from White's point of view, even if the "
    "board is drawn from Black's side - say so in `flipped`). Use the move indicator, highlighted last "
    "move or caption to decide whose move it is; if nothing shows it, guess and lower `confidence`. "
    "Mention any square you were unsure of in `notes`."
)


def fen_from_image(data_b64: str, media_type: str) -> dict:
    """{fen, confidence, notes} for a screenshot; raises ValueError if no legal position comes back."""
    if media_type not in MEDIA_TYPES:
        raise ValueError("Use a PNG, JPEG, WebP or GIF screenshot.")
    raw = base64.b64decode(data_b64, validate=True)
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("That screenshot is over 5 MB.")
    out = _json_response(
        [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data_b64}},
            {"type": "text", "text": FEN_PROMPT},
        ],
        FEN_SCHEMA,
    )
    return checked_fen(out)


def checked_fen(out: dict) -> dict:
    """Builds a full FEN from the model's reading and keeps it only if python-chess accepts it."""
    board = chess.Board(None)
    try:
        board.set_board_fen(out["placement"].strip())
    except ValueError as exc:
        raise ValueError("The board couldn't be read as a position.") from exc
    board.turn = out["side_to_move"] == "w"
    # Castling rights are only claimed when king and rook still stand on their home squares.
    rights = ""
    if board.piece_at(chess.E1) == chess.Piece(chess.KING, chess.WHITE):
        rights += "K" if board.piece_at(chess.H1) == chess.Piece(chess.ROOK, chess.WHITE) else ""
        rights += "Q" if board.piece_at(chess.A1) == chess.Piece(chess.ROOK, chess.WHITE) else ""
    if board.piece_at(chess.E8) == chess.Piece(chess.KING, chess.BLACK):
        rights += "k" if board.piece_at(chess.H8) == chess.Piece(chess.ROOK, chess.BLACK) else ""
        rights += "q" if board.piece_at(chess.A8) == chess.Piece(chess.ROOK, chess.BLACK) else ""
    board.set_castling_fen(rights or "-")
    if not board.is_valid():
        raise ValueError("What was read isn't a legal position. Try a clearer screenshot or type the FEN.")
    return {"fen": board.fen(), "confidence": out.get("confidence", "low"), "notes": out.get("notes", ""), "flipped": bool(out.get("flipped"))}


SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "A short title for the position, 3-8 words"},
        "summary": {"type": "string", "description": "One or two plain sentences: the idea the commentator explains"},
        "ideas": {"type": "array", "items": {"type": "string"}, "description": "Up to 3 concrete ideas or moves mentioned"},
    },
    "required": ["title", "summary", "ideas"],
    "additionalProperties": False,
}


def summarize_excerpt(text: str, fen: str | None = None) -> dict:
    """{title, summary, ideas} from a transcript excerpt (and the position, when known)."""
    text = text.strip()
    if not text:
        raise ValueError("There is no transcript to summarise.")
    prompt = (
        "Below is what a chess commentator says around one moment of a video"
        + (f", at this position (FEN): {fen}" if fen else "")
        + ". Summarise the idea they explain for a player who wants to remember it: a short title, one or "
        "two plain sentences, and up to three concrete ideas or moves they mention. Use only what the "
        "transcript says; do not add engine analysis or invent moves. Transcripts are auto-generated, so "
        "read move names generously (\"knight f5\" is Nf5).\n\n<transcript>\n" + text[:12000] + "\n</transcript>"
    )
    out = _json_response([{"type": "text", "text": prompt}], SUMMARY_SCHEMA)
    out["ideas"] = [i for i in out.get("ideas", []) if i.strip()][:3]
    return out
