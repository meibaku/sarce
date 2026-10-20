"""
Positions from a reference player's games for Train's "Tal in your openings" drill.

Usage (from apps/api):
    python -m scripts.build_reference_positions --zip path/to/Tal.zip

Reads a local pgnmentor ZIP (never downloads) and keeps one position per game: the first move the
player made between moves 12 and 30 that captures or gives check (where the game turned concrete),
or move 15 when there is none. Each entry keeps the game's ECO so Train can match your openings.
Writes data/reference_positions.json. Engine-free; a few seconds.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chess.pgn  # noqa: E402

from app.services.reference import TAL_PLAYER_NAME, ReferenceService, _matches_player_name  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "reference_positions.json"
FIRST, LAST, FALLBACK = 12, 30, 15


def pick(game: chess.pgn.Game, player: str) -> dict | None:
    """The drill position from one game, or None when the player isn't in it or it ends too soon."""
    white, black = game.headers.get("White", ""), game.headers.get("Black", "")
    if _matches_player_name(white, player):
        color = chess.WHITE
    elif _matches_player_name(black, player):
        color = chess.BLACK
    else:
        return None
    board, fallback = game.board(), None
    for move in game.mainline_moves():
        if board.turn == color and FIRST <= board.fullmove_number <= LAST:
            entry = {"fen": board.fen(), "san": board.san(move), "uci": move.uci()}
            if board.fullmove_number == FALLBACK:
                fallback = entry
            if board.is_capture(move) or board.gives_check(move):
                return entry
        board.push(move)
    return fallback


def build(zip_path: Path, player: str = TAL_PLAYER_NAME) -> list[dict]:
    out = []
    for text in ReferenceService._extract_pgns(zip_path, 100_000):
        game = chess.pgn.read_game(io.StringIO(text))
        if game is None:
            continue
        entry = pick(game, player)
        eco = game.headers.get("ECO", "")
        if entry is None or len(eco) != 3:
            continue
        opponent = game.headers.get("Black" if _matches_player_name(game.headers.get("White", ""), player) else "White", "")
        out.append({**entry, "eco": eco, "year": game.headers.get("Date", "")[:4], "opponent": opponent, "event": game.headers.get("Event", "")})
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reference positions for Train")
    parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    positions = build(args.zip)
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    data["Tal"] = positions
    OUT.write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Tal: {len(positions)} positions -> {OUT}")
