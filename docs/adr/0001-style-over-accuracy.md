# ADR-0001: Style Over Accuracy

## Status

Accepted; decision 2 superseded by [ADR 0012](./0012-learning-evidence-and-progress-semantics.md)

## Context

Most chess tools optimize for engine accuracy. Sarce exists because the founder
wants to **become a certain kind of player** (Tal-inspired: sacrificial, tactical)
— not maximize centipawn accuracy.

## Decision

1. **Brilliant** is a first-class move tier, not a subset of Best.
2. **Superseded:** Brilliant % was the universal headline dashboard metric. ADR 0012 keeps it prominent for an
   optional style goal while reporting learning evidence separately.
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

- `test_philosophy_contracts.py` — enforces the Brilliant tier and ADR 0012's style/learning boundary
- PR template — human review for punitive copy
