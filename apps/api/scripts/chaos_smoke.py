"""
Chaos Lens smoke run — the whole pipeline on one PGN, with a real engine and no database.

Usage:
    cd apps/api
    python -m scripts.chaos_smoke [game.pgn] [--color white] [--nodes 200000] [--opponent-rating 1500]

Runs Phase 1 classification, position evaluations, human move probabilities, lens
scoring and the intention tagger, keeping everything in memory, then prints what the
lenses found. Without a PGN it uses Morphy's Opera Game (1858). Needs STOCKFISH_PATH.
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

import chess.pgn

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.services import position_evals
from app.services.human_model import cached_move_probs, elo_ladder, get_human_model
from app.services.lens_service import build_ply_contexts, score_contexts, summarize
from app.services.move_classifier import MoveClassifier
from app.services.stockfish import StockfishEngine
from app.services.tagger import tag_game_data

OPERA_GAME = (
    "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7 "
    "8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7 "
    "14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0"
)


class MemoryStore:
    """In-memory stand-in for both cache tables."""

    def __init__(self) -> None:
        self.rows: dict[tuple, dict] = {}

    def get(self, *key):
        return self.rows.get(key)

    def put(self, row: dict) -> None:
        key = (row["fen_key"], row["nodes"]) if "nodes" in row else (row["fen_key"], row["elo"], row["model_version"])
        self.rows[key] = row


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Chaos Lens pipeline on one PGN")
    parser.add_argument("pgn", nargs="?", help="PGN file (default: the Opera Game)")
    parser.add_argument("--color", choices=["white", "black"], default="white")
    parser.add_argument("--nodes", type=int, default=200_000)
    parser.add_argument("--opponent-rating", type=int, default=1500)
    args = parser.parse_args()

    pgn_text = Path(args.pgn).read_text(encoding="utf-8") if args.pgn else OPERA_GAME
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise SystemExit("Could not parse the PGN")
    board, moves = game.board(), list(game.mainline_moves())
    settings.analysis_nodes = args.nodes

    started = time.time()
    classified = MoveClassifier().classify_game(board, moves, args.color)
    print(f"Phase 1: {len(classified)} user moves classified in {time.time() - started:.0f}s")

    evals, probs = MemoryStore(), MemoryStore()
    started = time.time()
    with StockfishEngine() as engine:
        stats = position_evals.evaluate_game_positions(board, moves, args.color, classified, engine, evals)
    print(f"Position evals at {args.nodes} nodes: {stats} in {time.time() - started:.0f}s")

    model = get_human_model(settings.human_model)
    for _ply, position in position_evals.iter_live_positions(board, moves, args.color, classified):
        for elo in elo_ladder(args.opponent_rating):
            cached_move_probs(position, elo, model, probs)

    probs_by_key: dict[str, dict[int, dict]] = {}
    for (key, elo, _version), row in probs.rows.items():
        probs_by_key.setdefault(key, {})[elo] = row["probs"]
    move_rows = [{**m, "id": f"move-{m['ply']}"} for m in classified]
    contexts = build_ply_contexts(
        pgn_text, move_rows, {key: row for (key, _nodes), row in evals.rows.items()}, probs_by_key, args.opponent_rating
    )
    rows = score_contexts("smoke", contexts)

    san_by_ply = {m["ply"]: m["san"] for m in classified}
    print(f"\nLens results (human model: {model.model_version} — uncalibrated):")
    for row in rows:
        if row["lens"] == "soundness" or (row["lens"] == "chaos" and not row["score"]):
            continue
        number = row["ply"] // 2 + 1
        print(f"  {number}. {san_by_ply[row['ply']]:<8} {row['lens']:<9} score={row['score']:.3f} verdict={row['verdict']}")
    print("Summary:", summarize(rows))

    tagged = tag_game_data(pgn_text, args.color, classified)
    print(f"\nMotif tags: {len(tagged['tags'])}; ideas: {tagged['ideas']}")


if __name__ == "__main__":
    main()
