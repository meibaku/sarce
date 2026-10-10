"""
Build the rating-band trap atlas from validation samples — Chaos Lens M6.

Usage:
    cd apps/api
    python -m scripts.build_trap_atlas [--samples scripts/out/chaos_samples.csv] [--dry-run]

Reads the per-position samples written by scripts/validate_chaos.py, keeps positions
where the most-played reply at a rating band loses at least 0.20 EP, and upserts them
into `trap_atlas`. Run validate_chaos with a low --min-ply so opening positions repeat.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.trap_atlas import TrapAtlasService, build_traps

DEFAULT_SAMPLES = Path(__file__).resolve().parent / "out" / "chaos_samples.csv"


def load_observations(path: Path) -> list[dict]:
    observations = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if not row.get("fen_key") or not row.get("reply_uci"):
                continue
            observations.append(
                {
                    **row,
                    "band": int(row["band"]),
                    "reply_ep_loss": float(row["reply_ep_loss"]),
                    "eco": row.get("eco") or None,
                    "best_reply_uci": row.get("best_reply_uci") or None,
                }
            )
    return observations


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the trap atlas from validation samples")
    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--dry-run", action="store_true", help="Print the result without writing")
    args = parser.parse_args()

    traps = build_traps(load_observations(args.samples))
    print(f"{len(traps)} traps found in {args.samples}")
    for trap in traps[:10]:
        print(f"  band {trap['band']}: {trap['common_reply_uci']} loses {trap['ep_loss']:.2f} EP ({trap['frequency']}x) {trap['fen']}")
    if not args.dry_run and traps:
        print(f"Saved {TrapAtlasService().save(traps)} rows to trap_atlas.")


if __name__ == "__main__":
    main()
