"""
Backfill Chaos Lens raw data for games that were analysed without it.

Usage:
    cd apps/api
    python -m scripts.backfill_chaos [--limit 20] [--username your_chess_com_name]

Runs the position-evaluation and human-probability pass, then lens scoring, for analysed
games whose `chaos_data_status` is empty or `failed`. Needs the Chaos Lens migrations and
a local Stockfish. Runs regardless of POSITION_EVALS_ENABLED, since it is an explicit request.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.analysis import AnalysisService


async def main(limit: int, username: str | None) -> None:
    result = await AnalysisService().backfill_chaos_data(limit=limit, username=username)
    print(f"Backfill attempted for {result['attempted']} games, skipped {result['skipped']}.")
    print("Check games.chaos_data_status for the outcome of each game.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill Chaos Lens raw data")
    parser.add_argument("--limit", type=int, default=20, help="Games per run")
    parser.add_argument("--username", default=None, help="Only this Chess.com username")
    args = parser.parse_args()
    asyncio.run(main(args.limit, args.username))
