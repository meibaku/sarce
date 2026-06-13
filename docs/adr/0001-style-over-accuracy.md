# ADR-0001: Style Over Accuracy

## Status

Accepted

## Context

Most chess tools optimize for engine accuracy. Sarce exists because the founder
wants to **become a certain kind of player** (Tal-inspired: sacrificial, tactical)
— not maximize centipawn accuracy.

## Decision

1. **Brilliant** is a first-class move tier, not a subset of Best.
2. **Brilliant %** is the headline dashboard metric toward a 6–10% target band.
3. Stockfish provides eval deltas and soundness checks; it does **not** define
   the user's goal function.
4. UX copy frames deviations as *distance from style goal*, never as moral failure.

## Consequences

### Positive

- Product differentiated from Chess.com / Lichess analysis
- Clear testable invariants (`test_philosophy_contracts.py`)
- Tal benchmark provides historical calibration

### Negative / trade-offs

- Brilliant heuristics are approximate; need golden tests + Tal corpus tuning
- Users chasing style may play unsound chess — we accept this as user intent

## Philosophy alignment

Fully aligned with [PHILOSOPHY.md](../PHILOSOPHY.md).

## Gates affected

- `test_philosophy_contracts.py` — enforces Brilliant tier + headline metric
- PR template — human review for punitive copy
