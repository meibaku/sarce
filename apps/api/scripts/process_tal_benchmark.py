"""
Tal reference benchmark batch job.

Usage:
    cd apps/api
    python -m scripts.process_tal_benchmark [--max-games 5]

Downloads Tal PGN corpus from pgnmentor.com, runs classification pipeline,
caches results in reference_benchmarks. See docs/PHASES.md Stage 1.9.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.reference import ReferenceService


async def main(max_games: int) -> None:
    service = ReferenceService()
    result = await service.process_tal_benchmark(max_games=max_games)
    print(f"Tal benchmark complete: {result['gamesSampled']} games")
    print(f"Brilliant %: {result['brilliantPct']:.2f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Tal reference benchmark")
    parser.add_argument("--max-games", type=int, default=5, help="Games to analyze (local dev: 5)")
    args = parser.parse_args()
    asyncio.run(main(args.max_games))
