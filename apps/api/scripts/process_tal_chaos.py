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
from app.services.position_evals import game_lines, iter_live_positions  # noqa: E402
from app.services.reference import TAL_PLAYER_NAME, ReferenceService, _matches_player_name  # noqa: E402
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


def score_game(pgn_text: str, classifier, engine, model, player: str = TAL_PLAYER_NAME) -> tuple[list[dict], list[dict]] | None:
    """(moves, lens rows) for the reference player's side of one game; None when they did not play in it."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return None
    board, moves = game.board(), list(game.mainline_moves())
    # Only games the player is in: some corpora hold games between relatives or rivals (e.g. the
    # Morphy collection), and a fallback colour would score someone else.
    if _matches_player_name(game.headers.get("White", ""), player):
        color = "white"
    elif _matches_player_name(game.headers.get("Black", ""), player):
        color = "black"
    else:
        return None
    evals, probs = MemoryEvalStore(), MemoryProbStore()
    # One search per position, as in the app: classification reads the lines the lenses use.
    classified = classifier.classify_game(board, moves, color, lines=game_lines(board, moves, engine, evals))
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


def _score_one(args) -> tuple[int, tuple[list[dict], list[dict]] | None, str | None]:
    """One game with its own engine, so games run in parallel (one engine per worker)."""
    i, pgn_text, model, player = args
    try:
        with StockfishEngine() as engine:
            return i, score_game(pgn_text, MoveClassifier(), engine, model, player), None
    except Exception as exc:  # one odd PGN must not stop the batch
        return i, None, str(exc)


def main(zip_path: Path, max_games: int, workers: int | None = None, player: str = TAL_PLAYER_NAME, key: str = "Tal") -> None:
    from concurrent.futures import ThreadPoolExecutor

    # The corpus is in date order, so the first N games would all be the teenage Tal: take an
    # evenly spaced sample across the whole career instead.
    corpus = ReferenceService._extract_pgns(zip_path, 100_000)
    step = max(1, len(corpus) // max_games)
    pgns = corpus[::step][:max_games]
    model = get_human_model(settings.human_model)
    all_moves: list[dict] = []
    all_lens: list[dict] = []
    scored = 0
    with ThreadPoolExecutor(workers or settings.workers) as pool:
        for i, result, error in pool.map(_score_one, [(i, p, model, player) for i, p in enumerate(pgns, 1)]):
            if error or result is None:
                print(f"game {i}: skipped ({error or 'unreadable'})", flush=True)
                continue
            moves, lens = result
            all_moves += moves
            all_lens += lens
            scored += 1
            print(f"game {i}/{len(pgns)}: {len(moves)} moves", flush=True)
    axes = axis_values(trait_values(all_moves, all_lens))
    data = json.loads(PATH.read_text(encoding="utf-8")) if PATH.exists() else {}
    data[key] = {
        "games": scored,
        "axes": axes,
        "model": model.name,
        "source": f"pgnmentor.com {key} corpus, every {step}th of {len(corpus)} games",
        "computedAt": datetime.now(timezone.utc).date().isoformat(),
    }
    PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"{key}: {scored} games -> {axes}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score a reference player's games on the You axes")
    parser.add_argument("--zip", type=Path, required=True, help="Local copy of the player's pgnmentor ZIP")
    parser.add_argument("--player", default=TAL_PLAYER_NAME, help='Full name as "First Last", e.g. "Alexei Shirov"')
    parser.add_argument("--key", default="Tal", help="Name shown on the You axes, e.g. Shirov")
    parser.add_argument("--max-games", type=int, default=40)
    parser.add_argument("--workers", type=int, default=None, help="Parallel engines (default: cores - 1)")
    args = parser.parse_args()
    main(args.zip, args.max_games, args.workers, args.player, args.key)
