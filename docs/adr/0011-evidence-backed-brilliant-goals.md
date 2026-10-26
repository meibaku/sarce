# ADR 0011: Evidence-backed Brilliant goal bands

**Status:** Accepted
**Date:** 2026-10-26

## Context

Sarce originally used a 6–10% Brilliant goal as a founder aspiration. Under the production v4 rule, Maia-2 and the
production-depth Stockfish search, the fixed 200-game Mikhail Tal corpus produced 20 Brilliants in 7,013 moves:
0.29%, with a game-bootstrap 95% interval of 0.17–0.41%. The complete 3,208-game personal snapshot produced 18
Brilliants in 69,786 reportable moves: 0.03%, with an interval of 0.01–0.04%.

The legacy band is therefore not calibrated to the metric Sarce now computes. Keeping it would present an admired
style reference as an unreachable numerical target.

## Decision

- The default Tal-style goal is **0.2–0.6% Brilliant**.
- The “More solid” goal is **0.0–0.2% Brilliant**.
- Goal values remain percentage points and clients preserve 0.1-point precision.
- Only rows still exactly equal to the legacy 6–10 defaults are migrated. Customized goals are never overwritten.
- Brilliant remains a first-class tier and Brilliant % remains a prominent optional style metric; ADR 0012 separately
  governs learning evidence and removes any universal progress score.

## Consequences

The API owns the canonical constants. Web and mobile display those bands without integer rounding. Very low current
intervals receive a 0.1–0.2% next step before the Tal band. Future rule or model changes require new versioned
evidence before defaults change again.

The full fixed-snapshot and Tal manifests are stored in `docs/evidence/phase1-closeout.json`; that generated artifact
also records rule, checkpoint and engine provenance.
