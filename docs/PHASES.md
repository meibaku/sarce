# Sarce — Phases & Implementation Status

> **Master specification:** [PRODUCT_SPEC.md](./PRODUCT_SPEC.md) — full product vision, Phases 1–4+, success metrics.

> **Philosophy:** [PHILOSOPHY.md](./PHILOSOPHY.md) — product constitution (CI-enforced).

This file tracks **what's built vs planned**. The phase definitions below match PRODUCT_SPEC.md.

---

## Phase 1 — MVP ✅ Complete

**Goal:** Import games, classify moves, detect Brilliant plays, track 6–10% target, Tal benchmark.

| Stage | Feature | Status |
|-------|---------|--------|
| 1.1 | Game import (Chess.com) | ✅ |
| 1.2 | Move classification (Stockfish) | ✅ |
| 1.3 | Brilliant detection (Tal rules) | ✅ |
| 1.4 | Baseline + dashboard | ✅ |
| 1.5 | Tal reference benchmark | ✅ |
| 1.6 | Tests + CI + quality gates | ✅ |
| 1.7 | Recent style moments + move drilldown | ✅ |
| 1.8 | ECO opening extraction | 🔲 |

---

## Phase 2 — Video & Transcript Context 🔲 Planned

**Goal:** Capture positions from videos; attach commentary; searchable position library.

| Stage | Feature | Status |
|-------|---------|--------|
| 2.1 | Manual position setter (`react-chessboard`) | 🔲 |
| 2.2 | Screenshot → FEN recognition | 🔲 |
| 2.3 | YouTube transcript capture | 🔲 |
| 2.4 | AI-summarized annotations | 🔲 |

---

## Phase 3 — Move Intent Journal 🔲 Planned

**Goal:** Post-game intent notes; intent vs engine reality; personal chess journal.

| Stage | Feature | Status |
|-------|---------|--------|
| 3.1 | Post-game annotation prompts | 🔲 |
| 3.2 | Intent vs reality comparison | 🔲 |
| 3.3 | Personal chess journal view | 🔲 |
| 3.4 | Narrative export (MD/PDF) | 🔲 |

---

## Phase 4+ — Future 🔲 Backlog

See [PRODUCT_SPEC.md § Phase 4+](./PRODUCT_SPEC.md#phase-4--future-enhancements-not-locked) for full list.

Highlights: Lichess import, reference player similarity, Android (Expo), opening matcher, anonymized peer comparison, browser extension, GM training mode.

---

## Classification reference

Rule-based from Stockfish (no ML). Details in [PRODUCT_SPEC.md § 1.2](./PRODUCT_SPEC.md#12-move-classification-engine-rule-based-no-ml) and `apps/api/app/services/move_classifier.py`.

**Brilliant criteria:** sacrifice + eval margin + not already winning + not forced — `brilliant.py`, tunable via `.env`.

---

## API endpoints (Phase 1, live)

| Method | Path |
|--------|------|
| POST | `/games/import` |
| GET | `/games` |
| GET | `/games/moments` |
| GET | `/games/{id}` |
| POST | `/games/analyze` |
| GET | `/analysis/baseline/{id}` |
| GET | `/analysis/timeline/{id}` |
| GET | `/reference/tal` |
