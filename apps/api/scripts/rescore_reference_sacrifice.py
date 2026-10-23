"""
Re-score only the "Sacrifices per 1,000 moves" axis of a reference player with the strict test (review F2). Board-only: no
engine, so it runs in seconds where the full reference scoring (process_tal_chaos.py) takes hours.

Usage:
    cd apps/api
    python -m scripts.rescore_reference_sacrifice --zip Tal.zip --player "Mikhail Tal" --key Tal [--max-games 40]

Uses the same evenly spaced sample as process_tal_chaos.py, so the value stays comparable with the player's other
axes, and the same share-of-moves definition as the You trait (you.trait_values).
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import chess.pgn

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.brilliant import MIN_BRILLIANT_SACRIFICE_VALUE, real_offer
from app.services.reference import ReferenceService, _matches_player_name
from app.services.reference_axes import PATH


def player_moves(pgn_text: str, player: str) -> tuple[int, int] | None:
    """(moves played by `player`, of which real sacrifices) in one game; None when they did not play in it."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return None
    if _matches_player_name(game.headers.get("White", ""), player):
        color = chess.WHITE
    elif _matches_player_name(game.headers.get("Black", ""), player):
        color = chess.BLACK
    else:
        return None
    board, moves, real = game.board(), 0, 0
    for move in game.mainline_moves():
        if board.turn == color:
            moves += 1
            real += real_offer(board, move) >= MIN_BRILLIANT_SACRIFICE_VALUE
        board.push(move)
    return moves, real


def main(zip_path: Path, player: str, key: str, max_games: int) -> None:
    corpus = ReferenceService._extract_pgns(zip_path, 100_000)
    step = max(1, len(corpus) // max_games)
    totals = [r for r in (player_moves(p, player) for p in corpus[::step][:max_games]) if r]
    moves = sum(m for m, _ in totals)
    real = sum(r for _, r in totals)
    rate = min(100, round(1000 * real / moves)) if moves else None  # per 1,000 moves, as reference_axes.axis_values
    data = json.loads(PATH.read_text(encoding="utf-8"))
    entry = data[key]
    old = entry["axes"].get("Sacrifices per 1,000 moves")
    entry["axes"]["Sacrifices per 1,000 moves"] = rate
    entry["sacrificeRule"] = "real_offer >= 3, per 1,000 moves (review F2)"
    entry["sacrificeComputedAt"] = datetime.now(timezone.utc).date().isoformat()
    PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"{key}: {len(totals)} games, {real} real sacrifices in {moves} moves -> Sacrifice rate {old} -> {rate}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-score a reference player's Sacrifice axis (strict test)")
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--player", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--max-games", type=int, default=40)
    args = parser.parse_args()
    main(args.zip, args.player, args.key, args.max_games)
