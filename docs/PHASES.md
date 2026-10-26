# Sarce — Phases & Implementation Status

> **Master specification:** [PRODUCT_SPEC.md](./PRODUCT_SPEC.md) — full product vision, Phases 1–4+, success metrics.

> **Philosophy:** [PHILOSOPHY.md](./PHILOSOPHY.md) — product constitution (CI-enforced).

> **Next:** [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) (ordered work items) · [REVIEW_2026-10.md](./REVIEW_2026-10.md) (findings) · [BENCHMARK.md](./BENCHMARK.md) · [COMPUTE.md](./COMPUTE.md)

> **Chaos Lens gameplan:** [CHAOS_PLAN.md](./CHAOS_PLAN.md) — milestone-by-milestone plan for the chaos/survival style lenses (post-Phase-1 work, run in parallel with the phases below).

This file tracks **what's built vs planned**. The phase definitions below match PRODUCT_SPEC.md.

---

## Product Phase 1 — MVP ✅ Complete

**Goal:** Import games, classify moves, detect Brilliant plays, track a Tal-calibrated target, Tal benchmark.

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

### October Analysis Foundation A1 — ✅ Complete

This is the later measurement-correctness programme from `IMPLEMENTATION_PLAN.md`, not the original MVP phase
above. Its fixed 3,208-game snapshot is complete, Maia-2 is routed by speed with style-vector v6 provenance, and
the 200-game Tal benchmark measured 0.29% Brilliant (95% game-bootstrap interval 0.17–0.41%). ADR 0011 therefore
sets the default Tal band to 0.2–0.6% and “More solid” to 0.0–0.2%. Full evidence is in
`docs/evidence/phase1-closeout.json`.

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

## Learning Evidence Phase 2 — Piece Safety 🟨 In progress

This research programme is distinct from the completed historical Product Phase 2 above. It asks whether Sarce can
show recognition, seven-day retention and later transfer for one deliberately narrow concept. The preregistered
contract is [LEARNING_EVIDENCE_PROTOCOL.md](./LEARNING_EVIDENCE_PROTOCOL.md); ADR 0012 separates learning evidence
from playing identity.

| Stage | Deliverable | Status |
| --- | --- | --- |
| LE2.1 | Learning ADR + preregistered protocol | ✅ |
| LE2.2 | Reviewed piece-safety detector and item bank | 🔲 |
| LE2.3 | Append-only attempts and rebuildable learning state | 🔲 |
| LE2.4 | Unlabelled web/mobile loop and Scheduler v2 | 🔲 |
| LE2.5 | Qualitative pilot | 🔲 |
| LE2.6 | Controlled day-7 pilot and transfer observer | 🔲 |
| LE2.7 | Evidence review ADR: go, revise or stop | 🔲 |

No second learning concept starts before LE2.6 reaches its day-7 endpoint.

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
