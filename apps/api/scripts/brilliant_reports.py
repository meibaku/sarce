"""
Where Sarce's Brilliant and other sites' part ways (plan 3.3, for Benchmark B in plan 4.2).

Usage:
    cd apps/api
    python -m scripts.brilliant_reports

Counts the "Chess.com called this Brilliant" reports by the clause Sarce's rule stopped at.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.brilliant_reports import clause_title, summary

if __name__ == "__main__":
    counts = summary()
    total = sum(counts.values())
    print(f"{total} report{'s' if total != 1 else ''}")
    for clause, n in counts.items():
        print(f"  {n:>4}  {clause_title(clause) if clause != 'unknown' else 'not enough data'}")
