"""
Brilliant % under the current rules (v3) for a reference player, and optionally for you (review F6).

Usage:
    cd apps/api
    python -m scripts.benchmark_brilliant_v3 --zip Tal.zip --player "Mikhail Tal" --key Tal --games 200 --workers 3
    python -m scripts.benchmark_brilliant_v3 --you

The reference run needs Stockfish (the app's shared search per position) and takes hours for 200 games; it uses an
evenly spaced sample across the career, like the other reference scripts. Results go to data/reference_brilliant.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.services.brilliant_benchmark import benchmark_game, player_report, summarize
from app.services.human_model import get_human_model
from app.services.reference import ReferenceService
from app.services.stockfish import StockfishEngine

OUT = Path(__file__).resolve().parents[1] / "data" / "reference_brilliant.json"


def save(key: str, summary: dict, **extra) -> None:
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    data[key] = {**summary, "rule": "v3 (find-rate-20 + real offer)", "computedAt": datetime.now(timezone.utc).date().isoformat(), **extra}
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def reference(zip_path: Path, player: str, key: str, games: int, workers: int) -> None:
    corpus = ReferenceService._extract_pgns(zip_path, 100_000)
    step = max(1, len(corpus) // games)
    pgns = corpus[::step][:games]
    model = get_human_model(settings.human_model)

    def one(args):
        i, pgn = args
        try:
            with StockfishEngine() as engine:
                return benchmark_game(pgn, player, engine, model)
        except Exception as exc:  # one odd PGN must not stop the run
            print(f"game {i}: skipped ({exc})", flush=True)
            return None

    results = []
    with ThreadPoolExecutor(workers) as pool:
        for i, r in enumerate(pool.map(one, enumerate(pgns, 1)), 1):
            if r:
                results.append(r)
            if i % 10 == 0:
                s = summarize(results)
                print(f"{i}/{len(pgns)} games · Brilliant {s['brilliantPct']}% {s['interval']} · stopped by {s['stoppedBy']}", flush=True)
    summary = summarize(results)
    save(key, summary, model=model.name, source=f"pgnmentor.com {key} corpus, every {step}th of {len(corpus)} games")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Brilliant % under rule v3 (review F6)")
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--player")
    parser.add_argument("--key")
    parser.add_argument("--games", type=int, default=200)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--you", action="store_true", help="Your analysed games, from stored data (no engine)")
    args = parser.parse_args()
    if args.you:
        summary = player_report(os.environ["LOCAL_USER_ID"])
        save("you", summary)
        print(json.dumps(summary, indent=2))
    else:
        reference(args.zip, args.player, args.key, args.games, args.workers)
