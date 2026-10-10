# ADR 0002 — Human move model for the Chaos Lens

## Status

Proposed — the interface and an interim model are implemented; the choice of trained model is **open**.

## Context

The Chaos Lens needs `P(move | position, Elo)`: how likely a human of a given rating is to find each
reply. [CHAOS_PLAN.md](../CHAOS_PLAN.md) (M2) calls for a rating-conditioned model such as Maia-2 or
Maia-3 rather than hand-made heuristics, chosen after a half-day spike.

That spike has **not** been run. It needs a heavy dependency (PyTorch or an ONNX runtime), which the
plan's ground rule 8 says to ask about first, and it needs a decision on licence and install cost
that belongs to the maintainer.

## Decision

1. All models sit behind `HumanModel` in `apps/api/app/services/human_model.py`:
   `move_probs(board, elo) -> {uci: probability}` covering **every legal move** and summing to 1.
2. Output is cached in `human_probs`, keyed by `(fen_key, elo, model_version)`, so switching model
   never overwrites older rows and never requires re-running Stockfish.
3. Probabilities are stored at the ladder `800 / 1200 / 1600 / 2000 / 2400` plus the opponent's
   rating rounded to 100.
4. Until a trained model is chosen, `HeuristicHumanModel` (`heuristic-1`) is the default. It scores
   captures, checks, promotions and forward moves without an engine. It is the comparison baseline
   M4 already asks for — it is **not** a calibrated human model.

## Still to decide (the spike)

| Question | How to answer it |
| --- | --- |
| Maia-2 or Maia-3 | Time 200 positions each on CPU; record ms/position |
| Install cost on Windows | Record the exact steps and package sizes |
| Licence | Read each project's licence for the intended use before depending on it |
| Full distribution | Confirm the model returns a probability for every legal move, not only top candidates |

The chosen model becomes a new `HumanModel` subclass selected with `HUMAN_MODEL`; nothing else changes.

## Consequences

### Positive

- Lenses, storage and the review UI can be built and tested now.
- The model is swappable; cached rows are versioned.

### Negative / trade-offs

- Chaos scores produced with `heuristic-1` are not calibrated to real players and must not be
  presented as "N in 10 players miss this" until M4 validates a trained model.
- No model handles bullet clocks; that adjustment stays in M4.

## Philosophy alignment

Aligned with [PHILOSOPHY.md](../PHILOSOPHY.md): the model describes how humans play, it does not judge
the user. Move classification stays rule-based — this model only estimates opponents' replies, so the
"no ML for classification in Phase 1" rule is untouched. Adding a trained model is the kind of change
that rule requires an ADR for; this is that ADR, and it stays *Proposed* until the model is chosen.

## Gates affected

- `tests/test_human_model.py` — every model must return a full, normalized distribution.
- `tests/test_philosophy_contracts.py` (no ML dependencies) will need an explicit exception when a
  trained model is added.
