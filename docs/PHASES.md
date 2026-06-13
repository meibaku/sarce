# Sarce — Phases & Stages

## Phase 1 — MVP (Tal-style personal tracker)

**Goal:** Import your games, classify move quality, detect Brilliant sacrificial
moves, track progress toward 6–10% Brilliant target, compare against Tal benchmark.

| Stage | Feature | Status | Key files |
|-------|---------|--------|-----------|
| 1.1 | Monorepo scaffold | ✅ Done | `package.json`, `apps/*` |
| 1.2 | Supabase schema + RLS | ✅ Done | `supabase/migrations/*` |
| 1.3 | Chess.com import | ✅ Done | `services/chess_com.py`, `routers/games.py` |
| 1.4 | Stockfish classification | ✅ Done | `services/stockfish.py`, `move_classifier.py` |
| 1.5 | Brilliant detection (Tal) | ✅ Done | `services/brilliant.py` |
| 1.6 | Analysis pipeline + persist | ✅ Done | `services/analysis.py` |
| 1.7 | Baseline aggregation | ✅ Done | `services/baseline.py` |
| 1.8 | Dashboard (live data) | ✅ Done | `apps/web/src/components/*` |
| 1.9 | Tal reference benchmark | ✅ Done | `scripts/process_tal_benchmark.py` |
| 1.10 | Tests | ✅ Done | `apps/api/tests/*` |

### Phase 1 API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health |
| POST | `/games/import` | Import Chess.com games + queue analysis |
| GET | `/games` | List games for user/username |
| POST | `/games/analyze` | Analyze pending games |
| GET | `/analysis/baseline/{id}` | User baseline (Brilliant %, distribution) |
| GET | `/analysis/timeline/{id}` | Brilliant % per game over time |
| GET | `/reference/tal` | Cached Tal benchmark |

---

## Phase 2 — Reference players

**Goal:** Compare your style to any admired player (Chess.com username).

| Stage | Feature | Status |
|-------|---------|--------|
| 2.1 | User picks reference players | 🔲 Planned |
| 2.2 | Pull + cache reference games | 🔲 Planned |
| 2.3 | Style vector similarity score | 🔲 Planned |
| 2.4 | UI: "80% similar to [Player]" | 🔲 Planned |

Schema ready: `reference_players`, `reference_benchmarks`, `style_vectors`.

---

## Phase 3 — Polish

**Goal:** Per-move insights, adjustable goals, optional community.

| Stage | Feature | Status |
|-------|---------|--------|
| 3.1 | Per-move highlight view | 🔲 Planned |
| 3.2 | Adjustable style goal settings | 🔲 Planned |
| 3.3 | Community style groupings | 🔲 Planned |

Schema ready: `profiles.style_goal`, `game_moves` eval data for drill-down.

---

## Classification tiers (Chess.com-style)

Rule-based from Stockfish centipawn loss (no ML):

| Tier | Centipawn loss |
|------|----------------|
| Best | 0 |
| Excellent | ≤ 25 |
| Good | ≤ 50 |
| Inaccuracy | ≤ 100 |
| Mistake | ≤ 200 |
| Blunder | > 200 |
| Miss | Had winning advantage, lost it (see `move_classifier.py`) |
| Brilliant | Sacrifice + eval within margin (see `brilliant.py`) |

---

## Brilliant detection (Tal-specific)

A move is **Brilliant** when ALL hold:

1. Material sacrifice (piece value given up)
2. Eval after move within `BRILLIANT_EVAL_MARGIN` of best (default 0.3 pawns)
3. Position not already winning by `BRILLIANT_WINNING_MARGIN` (default 3.0)
4. More than one reasonable legal move existed

Thresholds are env-tunable for calibration against Tal corpus.
