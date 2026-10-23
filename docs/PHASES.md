# Sarce — Phases & Implementation Status

> **Master specification:** [PRODUCT_SPEC.md](./PRODUCT_SPEC.md) — full product vision, Phases 1–4+, success metrics.

> **Philosophy:** [PHILOSOPHY.md](./PHILOSOPHY.md) — product constitution (CI-enforced).

> **Next:** [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) (ordered work items) · [REVIEW_2026-10.md](./REVIEW_2026-10.md) (findings) · [BENCHMARK.md](./BENCHMARK.md) · [COMPUTE.md](./COMPUTE.md)

> **Chaos Lens gameplan:** [CHAOS_PLAN.md](./CHAOS_PLAN.md) — milestone-by-milestone plan for the chaos/survival style lenses (post-Phase-1 work, run in parallel with the phases below).

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
| 1.8 | ECO opening extraction (`games.eco`, `games.opening`) | ✅ |

---

## Phase 2 — Video & Transcript Context ✅ Complete

**Goal:** Capture positions from videos; attach commentary; searchable position library.

| Stage | Feature | Status |
|-------|---------|--------|
| 2.1 | Manual position setter (FEN + preview, saved positions in Train) | ✅ |
| 2.2 | Screenshot → FEN recognition (Claude vision, opt-in; FEN checked by python-chess) | ✅ |
| 2.3 | YouTube transcript capture (captions around the moment; paste fallback when YouTube blocks) | ✅ |
| 2.4 | AI-summarized annotations (Claude, opt-in) + searchable position library | ✅ |

---

## Phase 3 — Move Intent Journal ✅ Complete

**Goal:** Post-game intent notes; intent vs engine reality; personal chess journal.

| Stage | Feature | Status |
|-------|---------|--------|
| 3.1 | Post-game annotation prompts (Summary question rotation, Review intent notes) | ✅ |
| 3.2 | Intent vs reality comparison (engine hidden until the intent is noted) | ✅ |
| 3.3 | Personal chess journal view (sacrifice library, notes) | ✅ |
| 3.4 | Narrative export (Markdown, print-to-PDF `/journal`) | ✅ |

---

## Phase 4+ — Future 🔲 Backlog

See [PRODUCT_SPEC.md § Phase 4+](./PRODUCT_SPEC.md#phase-4--future-enhancements-not-locked) for full list.

Highlights: Lichess import (✅ done, with automatic sync), reference player similarity (✅ Tal, Shirov and Morphy on the You axes, and
"Tal in your openings" in Train), Android/iOS (✅ `apps/mobile`, Expo), opening
matcher, anonymized peer comparison, browser extension, GM training mode.

---

## Classification reference

Rule-based from Stockfish (no ML). Details in [PRODUCT_SPEC.md § 1.2](./PRODUCT_SPEC.md#12-move-classification-engine-rule-based-no-ml) and `apps/api/app/services/move_classifier.py`.

**Brilliant criteria:** sacrifice + eval margin + not already winning + not forced — `brilliant.py`, tunable via `.env`.

---

## Chaos Lens endpoints

| Method | Path |
|--------|------|
| GET | `/games/{id}/lenses` |
| GET | `/users/{username}/chaos-summary` |
| GET | `/games/{id}/ideas` |
| GET | `/traps` |

---

## API endpoints (Phase 1, live; the v1.0 screens' endpoints are listed in `docs/DESIGN.md` and the routers)

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
