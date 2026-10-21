"""
Distraction check-ins: moves where the player's pace and choices changed in a way that time
pressure or difficulty doesn't explain. Sarce never says "you were distracted"; a flag only
picks which move the Summary check-in asks about ("Was something going on here?") and marks the
moment ?! in Review. The answers (game_answers.flagged) tell us whether the flags mean anything.

Signals, per user move, from the PGN clocks (games.clocks_ms, both sides per ply) and stored rows:
- rushed: a costly move (mistake or worse) played far faster than the player's own pace this game;
- unhurried miss: the opponent set a real problem (survival lens "missed") and the reply came fast;
- drift: a very long pause in a quiet position (no problem set, no chaos), the "looked away" pause.

Skipped on purpose: the opening (book and premoves), premoves (< 0.5 s), moves made in time trouble
(that is the "time pressure" answer, not this one) and correspondence games, where clocks say nothing.
"""

from __future__ import annotations

from statistics import median

COSTLY = {"mistake", "blunder", "miss"}
OPENING_PLIES = 16
PREMOVE_MS = 500
MIN_SAMPLES = 6
MAX_FLAGS = 3


def parse_time_control(tc: str | None) -> tuple[int, int] | None:
    """(base ms, increment ms) for "600" or "180+2"; None for daily ("1/86400") or unknown."""
    if not tc or "/" in tc:
        return None
    base, _, inc = tc.partition("+")
    try:
        return int(base) * 1000, int(inc or 0) * 1000
    except ValueError:
        return None


def move_times(clocks: list[int | None], plies: list[int], base_ms: int, inc_ms: int) -> dict[int, tuple[int, int]]:
    """ply → (time spent, own clock before the move), where the clocks allow it."""
    out = {}
    for ply in plies:
        if ply >= len(clocks) or clocks[ply] is None:
            continue
        before = base_ms if ply < 2 else clocks[ply - 2]
        if before is None:
            continue
        out[ply] = (max(0, before - clocks[ply] + inc_ms), before)
    return out


def flagged_plies(game: dict, moves: list[dict], lens_rows: list[dict]) -> list[int]:
    """Up to three flagged user plies, strongest first; [] when the game can't say."""
    tc = parse_time_control(game.get("time_control"))
    clocks = game.get("clocks_ms") or []
    if tc is None or not clocks:
        return []
    base_ms, inc_ms = tc
    times = move_times(clocks, [m["ply"] for m in moves], base_ms, inc_ms)
    sample = {p: t for p, t in times.items() if p >= OPENING_PLIES and t[0] >= PREMOVE_MS}
    if len(sample) < MIN_SAMPLES:
        return []
    pace = median(t[0] for t in sample.values()) or 1
    trouble_ms = max(10_000, base_ms // 10)

    quality = {m["ply"]: m.get("quality") for m in moves}
    survival = {r["ply"]: r.get("verdict") for r in lens_rows if r.get("lens") == "survival"}
    chaotic = {r["ply"] for r in lens_rows if r.get("lens") == "chaos" and r.get("verdict")}

    scores: dict[int, float] = {}
    for ply, (spent, before) in sample.items():
        if before < trouble_ms:
            continue
        ratio = spent / pace
        costly = quality.get(ply) in COSTLY
        if costly and ratio < 0.35:
            scores[ply] = 3 - ratio
        elif survival.get(ply) == "missed" and ratio < 0.5:
            scores[ply] = 2 - ratio
        elif ply not in survival and ply not in chaotic and spent >= 15_000 and ratio > 4:
            scores[ply] = 1 + min(ratio, 20) / 20 + (1 if costly else 0)
    return sorted(scores, key=lambda p: (-scores[p], p))[:MAX_FLAGS]
