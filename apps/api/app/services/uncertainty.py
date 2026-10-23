"""
Honest uncertainty for the numbers Sarce shows (review F4).

Brilliant moves and most trait events are rare, so a percentage alone overstates what a handful of games can say:
after five bullet games a 2% player and a 6% player can show the same number. Every rate gets a Wilson 95%
interval (well behaved near 0, unlike the normal approximation), a change is called "up" or "down" only when the
two intervals do not overlap, and any rate resting on fewer than MIN_EVENTS events is not shown at all.
"""

from __future__ import annotations

import math

Z = 1.96  # 95%
MIN_EVENTS = 30  # below this many events a rate is dashed, whatever the number of games
ROLLING_GAMES = 20  # the trend's window
ROLLING_STEP = 5
ROLLING_POINTS = 12


def wilson(k: float, n: float, z: float = Z) -> tuple[float, float] | None:
    """Wilson score interval for k successes in n trials, as fractions; None when there are no trials."""
    if n <= 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def direction(before: tuple[float, float] | None, after: tuple[float, float] | None) -> str | None:
    """"up" or "down" only when the intervals separate; None when they overlap (the change may be noise)."""
    if not before or not after:
        return None
    if after[0] > before[1]:
        return "up"
    if after[1] < before[0]:
        return "down"
    return None


def gated(value: float | None, events: int) -> float | None:
    """The value, or None when it rests on fewer than MIN_EVENTS events."""
    return value if events >= MIN_EVENTS else None
