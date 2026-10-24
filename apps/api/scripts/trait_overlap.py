"""
Do the nine fingerprint traits measure different things? (review F10a, implementation plan 1.9)

Your analysed games are cut into consecutive windows of WINDOW games (newest first). The traits are computed per
window exactly as the You screen does (`you.gated_traits`: under MIN_EVENTS events a value is dashed). Every pair's
Pearson correlation is taken over the windows where both have a value; pairs at |r| > FLAG move together and are
candidates to merge. Each trait's spread is reported too, since a trait that barely moves (a ceiling) says little.

Usage:
    cd apps/api
    python -m scripts.trait_overlap [--window 20] [--json out.json]

Reads stored data only (no engine). Prints the matrix; a merge or drop needs an ADR and the owner's decision.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from itertools import combinations
from pathlib import Path

# Allow running as script from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.you import TRAITS, gated_traits

WINDOW = 20
FLAG = 0.8
PAGE = 1000
CHUNK = 25  # game ids per request: lens rows are many, and a wide filter times out


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson's r, or None with fewer than three pairs or no variation."""
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return None if sxx == 0 or syy == 0 else sxy / math.sqrt(sxx * syy)


def matrix(windows: list[dict[str, float | None]]) -> dict[tuple[str, str], tuple[float | None, int]]:
    """{(a, b): (r, windows used)} for every trait pair, over windows where both are known."""
    out = {}
    for a, b in combinations(TRAITS, 2):
        pairs = [(w[a], w[b]) for w in windows if w.get(a) is not None and w.get(b) is not None]
        out[(a, b)] = (pearson([p[0] for p in pairs], [p[1] for p in pairs]), len(pairs))
    return out


def spread(windows: list[dict[str, float | None]]) -> dict[str, dict]:
    """Each trait's range across windows: a trait stuck near one value can't tell weeks apart."""
    out = {}
    for t in TRAITS:
        vals = sorted(w[t] for w in windows if w.get(t) is not None)
        out[t] = {"n": len(vals), "min": round(vals[0], 3), "median": round(vals[len(vals) // 2], 3), "max": round(vals[-1], 3)} if vals else {"n": 0}
    return out


def load(owner_id: str) -> tuple[list[dict], dict[str, list[dict]], dict[str, list[dict]]]:
    from app.db.supabase import get_supabase

    sb = get_supabase()
    games: list[dict] = []
    while True:
        batch = (
            sb.table("games").select("id").eq("user_id", owner_id).eq("analysis_status", "complete").neq("source", "sarce_bot")
            .order("played_at", desc=True).order("id").range(len(games), len(games) + PAGE - 1).execute().data
            or []
        )
        games += batch
        if len(batch) < PAGE:
            break

    def paged(build) -> list[dict]:
        rows: list[dict] = []
        while True:
            batch = build().range(len(rows), len(rows) + PAGE - 1).execute().data or []
            rows += batch
            if len(batch) < PAGE:
                return rows

    moves: dict[str, list[dict]] = {}
    lens: dict[str, list[dict]] = {}
    ids = [g["id"] for g in games]
    for start in range(0, len(ids), CHUNK):
        part = ids[start : start + CHUNK]
        for m in paged(lambda: sb.table("game_moves").select("id, game_id, signals").in_("game_id", part).order("id")):
            moves.setdefault(m["game_id"], []).append(m)
        for r in paged(
            lambda: sb.table("move_lens_scores").select("game_move_id, game_id, lens, score, verdict")
            .in_("game_id", part).in_("lens", ["chaos", "survival", "squeeze", "swindle", "clock", "prophylaxis"]).order("game_move_id").order("lens")
        ):
            lens.setdefault(r["game_id"], []).append(r)
    return games, moves, lens


def windows_of(games: list[dict], moves: dict, lens: dict, size: int) -> list[dict[str, float | None]]:
    out = []
    for start in range(0, len(games) - size + 1, size):
        part = games[start : start + size]
        values, _ = gated_traits(
            [m for g in part for m in moves.get(g["id"], [])], [r for g in part for r in lens.get(g["id"], [])]
        )
        out.append(values)
    return out


def main(window: int, out: Path | None) -> None:
    from app.config import settings

    games, moves, lens = load(settings.local_user_id)  # reads .env like the API
    windows = windows_of(games, moves, lens, window)
    m, s = matrix(windows), spread(windows)
    print(f"{len(games)} games in {len(windows)} windows of {window}\n")
    width = max(len(t) for t in TRAITS)
    print(" " * (width + 1) + " ".join(f"{t[:5]:>6}" for t in TRAITS))
    for a in TRAITS:
        cells = []
        for b in TRAITS:
            if a == b:
                cells.append(f"{'-':>6}")
                continue
            r, _ = m.get((a, b)) or m.get((b, a))
            cells.append(f"{'·':>6}" if r is None else f"{r:6.2f}")
        print(f"{a:<{width}} " + " ".join(cells))
    flagged = sorted(((a, b, r, n) for (a, b), (r, n) in m.items() if r is not None and abs(r) > FLAG), key=lambda x: -abs(x[2]))
    print("\nPairs moving together (|r| > %.1f): %s" % (FLAG, ", ".join(f"{a}–{b} {r:.2f} (n={n})" for a, b, r, n in flagged) or "none"))
    print("\nSpread across windows:")
    for t, v in s.items():
        print(f"  {t:<{width}} {v}")
    if out:
        out.write_text(json.dumps({"window": window, "windows": len(windows), "pairs": {f"{a}|{b}": {"r": None if r is None else round(r, 3), "n": n} for (a, b), (r, n) in m.items()}, "spread": s}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Correlation of the fingerprint traits (review F10a)")
    parser.add_argument("--window", type=int, default=WINDOW)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()
    main(args.window, args.json)
