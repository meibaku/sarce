"""
Scoring-model comparison (docs/COMPETITIVE.md): the same eval drops labelled by each tool's published rules.

Engine-free and dependency-free. Run: `python -m scripts.compare_scoring_models` from apps/api.

- Lichess: published Win% and per-move accuracy formulas (lichess.org/page/accuracy); judgements from the
  winning-chances drop (0.1 inaccuracy, 0.2 mistake, 0.3 blunder on the [-1, 1] scale).
- Chess.com: published expected-points cut-offs (support article "How are moves classified"). Their EP model is
  rating-aware and private, so EP is approximated here with the Lichess curve — a proxy, not their numbers.
- Sarce: the current centipawn-loss THRESHOLDS in app/services/move_classifier.py (Phase 1), mirrored here so the
  script runs without the API's dependencies.
"""

from __future__ import annotations

import math

SLOPE = 0.00368208  # Lichess; also ep.CP_TO_EP_SLOPE


def win_pct(cp: float) -> float:
    return 50 + 50 * (2 / (1 + math.exp(-SLOPE * cp)) - 1)


def lichess_accuracy(before: float, after: float) -> float:
    drop = max(0.0, win_pct(before) - win_pct(after))
    return max(0.0, min(100.0, 103.1668 * math.exp(-0.04354 * drop) - 3.1669))


def lichess_judgement(before: float, after: float) -> str:
    chances = lambda cp: 2 / (1 + math.exp(-SLOPE * cp)) - 1  # noqa: E731
    drop = chances(before) - chances(after)
    return "Blunder" if drop >= 0.3 else "Mistake" if drop >= 0.2 else "Inaccuracy" if drop >= 0.1 else "—"


def chesscom_tier(before: float, after: float) -> str:
    drop = (win_pct(before) - win_pct(after)) / 100
    for limit, tier in [(0.0, "Best"), (0.02, "Excellent"), (0.05, "Good"), (0.10, "Inaccuracy"), (0.20, "Mistake")]:
        if drop <= limit + 1e-9:
            return tier
    return "Blunder"


def sarce_tier(before: float, after: float) -> str:
    loss = max(0.0, before - after)
    for limit, tier in [(0, "Best"), (25, "Excellent"), (50, "Good"), (100, "Inaccuracy"), (200, "Mistake")]:
        if loss <= limit:
            return tier
    return "Blunder"


# (eval before, eval after) in centipawns, from the mover's side.
CASES = [
    (0, -100), (300, 200), (600, 500), (900, 800), (0, -200), (500, 300), (800, 400),
    (1000, 600), (-300, -400), (-600, -900), (150, -150), (0, -40), (400, 340),
]


def main() -> None:
    print("| Before → after (cp) | Loss | Win% drop | Lichess judgement | Lichess move accuracy | Chess.com tier (EP proxy) | Sarce tier (cp) |")
    print("|---|---|---|---|---|---|---|")
    agree = 0
    for before, after in CASES:
        cc, sa = chesscom_tier(before, after), sarce_tier(before, after)
        agree += cc == sa
        print(
            f"| {before:+d} → {after:+d} | {before - after} cp | {win_pct(before) - win_pct(after):.1f} | "
            f"{lichess_judgement(before, after)} | {lichess_accuracy(before, after):.0f}% | {cc} | {sa} |"
        )
    print(f"\nSarce agrees with the Chess.com proxy on {agree} of {len(CASES)} cases.")


if __name__ == "__main__":
    main()
