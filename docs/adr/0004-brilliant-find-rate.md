# ADR 0004: Brilliant also means hard to find

## Status

Accepted (v1.0 design handoff, product decision 1)

## Context

Brilliant is the headline metric (ADR 0001). Today a move is Brilliant when it is a real piece
sacrifice, stays within the excellent margin of the engine's best, is not played from an already
crushing position and is not forced (`app/services/brilliant.py`). Nothing asks whether a human
would have found it, so an obvious recapture-style sacrifice that most players at that rating play
counts the same as a hidden one. Players ask for exactly that distinction (the handoff's competitor
audit: "Brilliant should mean hard to find"), and Sarce already stores what it needs to answer it:
the Maia-2 probability of every move at each ladder rating (`human_probs`, ADR 0002).

## Decision

1. A move is Brilliant only if the four existing conditions hold **and** players at the relevant
   rating find it at most **20%** of the time (`FIND_RATE_MAX` in `brilliant.py`). The rating is the
   ladder rung nearest the opponent's rating, the same proxy the lenses use, because the player's
   own rating is not stored.
2. The check runs after the human-model probabilities are stored (the Chaos Lens pass, when
   `POSITION_EVALS_ENABLED` is on). Moves that fail it are re-classified as **best** and the game's
   distribution, Brilliant % and style vector are recomputed.
3. A game scored under the new rule gets `style_vector.version = 2` and
   `style_vector.brilliantRule = "find-rate-20"`. Games without human-model data keep version 1 and
   the old rule; they are never silently mixed: the version is on every vector.
4. `scripts/backfill_brilliant_find_rate.py` applies the rule to already-analysed games.
5. Trend charts mark the week the definition changed ("style v2"), so a drop in Brilliant % after
   the change reads as a new yardstick, not worse play.

## Consequences

### Positive

- Brilliant keeps its meaning as the Tal-style headline while matching what players mean by it.
- Uses data Sarce already stores; no new dependency.

### Negative / trade-offs

- Brilliant % will fall for most players once the rule applies, so the 6–10% band may need
  revisiting after a few weeks of v2 data. The marker on the trend explains the step.
- The check depends on the human model: with only the heuristic model installed, the find-rate is a
  rough estimate. The model in use is recorded in `human_probs.model_version`.
- Until the Chaos Lens pass runs for a game, that game is on the old rule.

## Philosophy alignment

Strengthens it: Brilliant stays first-class and the headline, and the new clause is about human
difficulty, the "mirror, not judge" view, not engine accuracy.

## Gates affected

- `tests/test_brilliant_find_rate.py` covers the clause, the re-classification and the v2 vector.
- `tests/test_philosophy_contracts.py` unchanged: the v1 builder still produces version 1.
