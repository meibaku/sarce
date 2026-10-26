"""
Brilliant % under the current production rule for a reference player and the fixed personal snapshot.

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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.services.brilliant_find_rate import RULE
from app.services.brilliant_benchmark import benchmark_game, even_sample, player_report, summarize
from app.db.supabase import get_supabase
from app.services.human_model import get_human_model
from app.services.reference import ReferenceService
from app.services.stockfish import StockfishEngine

OUT = Path(__file__).resolve().parents[1] / "data" / "reference_brilliant.json"


def save(key: str, summary: dict, **extra) -> None:
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    data[key] = {**summary, "rule": RULE, "computedAt": datetime.now(timezone.utc).date().isoformat(), **extra}
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def pgn_identity(pgn_text: str) -> tuple[str, str | None]:
    """A reviewable corpus identifier and date without claiming an external database ID."""
    import io

    import chess.pgn

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    headers = game.headers if game else {}
    date = headers.get("Date")
    label = "|".join(
        str(headers.get(key) or "?") for key in ("Date", "Round", "White", "Black")
    )
    return label, date


def ordered_checkpoint_results(
    identities: list[tuple[str, str | None]], saved: dict[str, dict]
) -> tuple[list[dict], set[str]]:
    """Restore sample order after concurrent work and ignore unrelated checkpoint rows."""
    rows = [saved[identity] for identity, _date in identities if identity in saved]
    return [row["result"] for row in rows], {row["engineVersion"] for row in rows}


def reference(
    zip_path: Path,
    player: str,
    key: str,
    games: int,
    workers: int,
    checkpoint: Path | None = None,
) -> None:
    corpus = ReferenceService._extract_pgns(zip_path, 100_000)
    pgns = even_sample(corpus, games)
    # Historical games without a usable clock are routed to rapid, exactly like production.
    model = get_human_model("maia2", "rapid")
    identities = [pgn_identity(pgn) for pgn in pgns]
    cache = {"rule": RULE, "model": model.model_version, "results": {}}
    if checkpoint and checkpoint.exists():
        saved = json.loads(checkpoint.read_text(encoding="utf-8"))
        if (saved.get("rule"), saved.get("model")) == (RULE, model.model_version):
            cache = saved

    def save_checkpoint() -> None:
        if not checkpoint:
            return
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        tmp = checkpoint.with_suffix(checkpoint.suffix + ".tmp")
        tmp.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
        tmp.replace(checkpoint)

    def one(args):
        i, pgn = args
        identity = identities[i - 1][0]
        if identity in cache["results"]:
            saved = cache["results"][identity]
            return saved["result"], saved["engineVersion"], identity, False
        try:
            with StockfishEngine() as engine:
                return benchmark_game(pgn, player, engine, model), engine.engine_version, identity, True
        except Exception as exc:  # one odd PGN must not stop the run
            print(f"game {i}: skipped ({exc})", flush=True)
            return None

    with ThreadPoolExecutor(workers) as pool:
        futures = {
            pool.submit(one, item): item[0]
            for item in enumerate(pgns, 1)
        }
        for completed, future in enumerate(as_completed(futures), 1):
            outcome = future.result()
            if outcome:
                r, engine_version, identity, is_new = outcome
                if r is None:
                    continue
                if is_new:
                    cache["results"][identity] = {
                        "result": r,
                        "engineVersion": engine_version,
                    }
                    save_checkpoint()
            if completed % 10 == 0:
                current = [entry["result"] for entry in cache["results"].values()]
                s = summarize(current)
                print(f"{completed}/{len(pgns)} games · Brilliant {s['brilliantPct']}% {s['interval']} · stopped by {s['stoppedBy']}", flush=True)
    # Restore sample order so the seeded bootstrap is reproducible despite concurrent completion.
    results, engine_versions = ordered_checkpoint_results(identities, cache["results"])
    if not results:  # e.g. no engine: keep the saved benchmark rather than overwrite it with nothing
        sys.exit(f"No {player} games were benchmarked; {OUT.name} left unchanged")
    summary = summarize(results)
    save(
        key,
        summary,
        corpusSize=len(corpus),
        gameIds=[identity for identity, _date in identities],
        cutoff=max((date for _identity, date in identities if date), default=None),
        modelCheckpoints=[model.model_version],
        engineVersions=sorted(engine_versions),
        source=f"pgnmentor.com {key} corpus, {len(pgns)} evenly spaced games",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Brilliant % under rule v3 (review F6)")
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--player")
    parser.add_argument("--key")
    parser.add_argument("--games", type=int, default=200)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--checkpoint", type=Path, help="Atomic, resumable Tal result checkpoint")
    parser.add_argument("--you", action="store_true", help="Your analysed games, from stored data (no engine)")
    parser.add_argument("--snapshot", type=Path, help="Fixed manifest required for the personal closeout report")
    args = parser.parse_args()
    if settings.human_model != "maia2":
        sys.exit("Closeout evidence requires HUMAN_MODEL=maia2")
    if args.you:
        if not args.snapshot:
            sys.exit("--you requires --snapshot for reproducible closeout evidence")
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        game_ids = set(snapshot["gameIds"])
        summary = player_report(os.environ["LOCAL_USER_ID"], game_ids=game_ids)
        engine_rows = get_supabase().table("position_evals").select("engine_version").limit(1000).execute().data or []
        save(
            "you",
            summary,
            corpusSize=snapshot["gameCount"],
            gameIds=snapshot["gameIds"],
            cutoff=snapshot["capturedAt"],
            modelCheckpoints=["maia2-0.11-blitz", "maia2-0.11-rapid"],
            engineVersions=sorted({row["engine_version"] for row in engine_rows if row.get("engine_version")}),
        )
        print(json.dumps(summary, indent=2))
    else:
        reference(args.zip, args.player, args.key, args.games, args.workers, args.checkpoint)
