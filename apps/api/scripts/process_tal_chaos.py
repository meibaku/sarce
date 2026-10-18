"""
Score Tal's games in the same chaos terms as yours, for the You axes.

Usage (from apps/api, with STOCKFISH_PATH set):
    python -m scripts.process_tal_chaos --zip path/to/Tal.zip [--max-games 40]

Reads the pgnmentor Tal corpus from a local ZIP (download it yourself; this script never fetches
anything), runs each game through Phase 1 classification and the Chaos Lens with Tal as the
"user", entirely in memory (no database writes), and writes the four axis values to
data/reference_axes.json. Classical games have no clocks, so the lens uses its no-clock bucket.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chess.pgn  # noqa: E402

from app.config import settings  # noqa: E402
from app.lenses.registry import score_ply  # noqa: E402
from app.services.human_model import cached_move_probs, elo_ladder, get_human_model  # noqa: E402
from app.services.lens_service import build_ply_contexts, keys_after_each_ply  # noqa: E402
from app.services.move_classifier import MoveClassifier  # noqa: E402
from app.services.position_evals import evaluate_game_positions, iter_live_positions  # noqa: E402
from app.services.reference import TAL_PLAYER_NAME, ReferenceService, infer_player_color  # noqa: E402
from app.services.reference_axes import PATH, axis_values  # noqa: E402
from app.services.stockfish import StockfishEngine  # noqa: E402
from app.services.you import trait_values  # noqa: E402


class MemoryEvalStore:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def get(self, key: str, nodes: int) -> dict | None:
        row = self.rows.get(key)
        return row if row and row["nodes"] == nodes else None

    def put(self, row: dict) -> None:
        self.rows[row["fen_key"]] = row


class MemoryProbStore:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, int], dict] = {}

    def get(self, key: str, elo: int, model_version: str) -> dict | None:
        return self.rows.get((key, elo))

    def put(self, row: dict) -> None:
        self.rows[(row["fen_key"], row["elo"])] = row


def opponent_rating(game: chess.pgn.Game, color: str) -> int | None:
    raw = game.headers.get("BlackElo" if color == "white" else "WhiteElo", "")
    return int(raw) if raw.isdigit() else None


def score_game(pgn_text: str, classifier, engine, model) -> tuple[list[dict], list[dict]] | None:
    """(moves, lens rows) for the reference player's side of one game."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return None
    board, moves = game.board(), list(game.mainline_moves())
    color = infer_player_color(game, TAL_PLAYER_NAME)
    classified = classifier.classify_game(board, moves, color)
    evals, probs = MemoryEvalStore(), MemoryProbStore()
    evaluate_game_positions(board, moves, color, classified, engine, evals)
    rating = opponent_rating(game, color)
    for _ply, position in iter_live_positions(board, moves, color, classified):
        for elo in elo_ladder(rating):
            cached_move_probs(position, elo, model, probs)
    probs_by_key: dict[str, dict[int, dict[str, float]]] = {}
    for (key, elo), row in probs.rows.items():
        probs_by_key.setdefault(key, {})[elo] = row["probs"]
    contexts = build_ply_contexts(pgn_text, classified, evals.rows, probs_by_key, rating, model_name=model.name)
    lens = [
        {"ply": ctx.ply, "lens": name, "score": result.score, "verdict": result.verdict}
        for _move, ctx in contexts
        for name, (_lens, result) in score_ply(ctx).items()
    ]
    return classified, lens


def main(zip_path: Path, max_games: int) -> None:
    pgns = ReferenceService._extract_pgns(zip_path, max_games)
    model = get_human_model(settings.human_model)
    classifier = MoveClassifier()
    all_moves: list[dict] = []
    all_lens: list[dict] = []
    scored = 0
    with StockfishEngine() as engine:
        for i, pgn_text in enumerate(pgns, 1):
            try:
                result = score_game(pgn_text, classifier, engine, model)
            except Exception as exc:  # one odd PGN must not stop the batch
                print(f"game {i}: skipped ({exc})", flush=True)
                continue
            if result is None:
                continue
            moves, lens = result
            all_moves += moves
            all_lens += lens
            scored += 1
            print(f"game {i}/{len(pgns)}: {len(moves)} moves", flush=True)
    axes = axis_values(trait_values(all_moves, all_lens))
    data = json.loads(PATH.read_text(encoding="utf-8")) if PATH.exists() else {}
    data["Tal"] = {
        "games": scored,
        "axes": axes,
        "model": model.name,
        "source": "pgnmentor.com Tal corpus",
        "computedAt": datetime.now(timezone.utc).date().isoformat(),
    }
    PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Tal: {scored} games -> {axes}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score Tal's games on the You axes")
    parser.add_argument("--zip", type=Path, required=True, help="Local copy of pgnmentor's Tal.zip")
    parser.add_argument("--max-games", type=int, default=40)
    args = parser.parse_args()
    main(args.zip, args.max_games)
