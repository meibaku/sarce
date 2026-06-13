# Sarce Philosophy

> **North star:** Did this game feel like *you* — not did you play like the engine?

This document is the product constitution. CI gates, architecture tests, and PR
review check against it. If a change conflicts with this doc, the change needs an
explicit ADR (`docs/adr/`) before merging.

---

## What we are

A **personal chess companion** that tracks progress toward a playing **identity**
you are actively building — not a tool that grades you against perfect accuracy.

For the founder: a **Tal-inspired** style with a target of **6–10% Brilliant**
(sacrificial, tactical, attacking) moves, tracked game by game.

## What we are not

| We are | We are not |
|--------|------------|
| Style-aware self-development | Generic engine accuracy coach |
| Celebrating intentional risk | Treating every sacrifice as a mistake |
| A mirror for who you're becoming | A judge scoring "correctness" |
| Light, enjoyable, personal | Homework, grind, guilt |

**Hard rule:** No user-facing copy, metric, or sort order may frame Brilliant or
sacrificial play as failure. Low Brilliant % is *distance from your goal*, not
*moral wrongness*.

---

## Core principles (non-negotiable)

### 1. Style is a legitimate goal

Sacrifices, complications, and calculated risk are **features of identity**, not
bugs to eliminate. Classification must preserve a **Brilliant** tier distinct
from Best/Excellent.

### 2. Engine as mirror, not judge

Stockfish informs *how far* a move deviated and *whether a sacrifice stayed sound*.
It does **not** define the user's goal function. The user's style target does.

### 3. Headline metric = Brilliant %

The primary progress signal is **Brilliant %** toward the user's target band
(default 6–10%). Full move-quality distribution provides context, never replaces
the headline.

### 4. Progress over time, game by game

Every analyzed game contributes to a **timeline** of style identity. Aggregates
must be rolling/per-game — not a single static score.

### 5. Reference benchmarks, not rankings

Tal (and future admired players) are **calibration references** — "what does this
style look like historically?" — not leaderboards or social comparison.

### 6. Versioned style schema

`style_vector.version` increments when features change. Never silently redefine
what "style" means.

### 7. Lightness

UX copy, notifications, and summaries should feel encouraging and curious:
*"right in your Tal-style target range"* — not punitive.

---

## Vision (later phases — guard but don't block MVP)

- Living record of chess identity: games, inspired positions, reasoning notes
- Reference players you admire (Phase 2)
- Per-move highlights toward *your* style, not engine line (Phase 3)
- Optional community — anonymized, never competitive leaderboard by default

---

## Enforcement

| Mechanism | What it guards |
|-----------|----------------|
| `tests/test_philosophy_contracts.py` | API/schema invariants |
| `tests/test_architecture.py` | Module boundaries, banned patterns |
| `tests/test_classifier.py` + golden fixtures | Classification tiers |
| `.github/workflows/ci.yml` | All gates on every PR |
| PR template | Human review against this doc |
| `docs/adr/` | Documented exceptions |
