# ADR 0009 — Brilliant rule v4: judged in expected points

## Status

Accepted (2026-10-24, approved by the owner). Amends [ADR 0004](./0004-brilliant-find-rate.md) and
[ADR 0007](./0007-brilliant-real-offer.md). Review F5 (`docs/REVIEW_2026-10.md`), implementation plan item 1.6.

## Context

Three Brilliant clauses did not match the spec they claimed to implement:

- **"Not forced"** only checked that more than one legal move existed. A sacrifice where every other move lost
  outright counted as a choice.
- **Lost positions** could produce Brilliant moves: a "sound" piece offer at −6 is a lost game played on, which is
  the swindle lens's job (fighting spirit), not Brilliant.
- **Soundness** was a fixed 0.25 pawns. A quarter-pawn decides a level game and means nothing at +4, so the clause
  was strict where it should be lenient and lenient where it should be strict. It also used the absolute
  difference, so a move that searched *better* than the best line failed as "unsound".

Chaos already measures everything in expected points (EP, CHAOS_PLAN rule 4); Brilliant was the exception.

## Decision

Rule v4, in expected points from the mover's side (`app/services/brilliant.py`):

1. **Sound:** the move loses at most `SOUND_EP_LOSS = 0.03` EP against the best move. One-sided: scoring above
   the best line is not a fault. (≈ 0.33 pawns when level, more when the game is one-sided.)
2. **Not lost:** EP before the move is at least `LOST_EP = 0.10`, the same "decided" line chaos uses.
3. **Not forced:** another move kept the mover within `ALTERNATIVE_EP = 0.10` EP of the best, read from the
   engine's lines before the move. With no line for any other move, more than one legal move is enough.
4. Unchanged: a real offer of at least a minor piece (ADR 0007), not already above +3 pawns, and found by at most
   20% of players at the mover's converted rating (ADR 0004 and its addendum).

`brilliant_clauses` returns the clauses in order (`CLAUSES`); `is_brilliant_move` is the board clauses
(`BOARD_CLAUSES`). The post-pass (`BrilliantFindRate.apply`) now judges every stored move **from scratch**, so a
rule change can promote as well as demote. Style vectors move to **version 5** / rule `v4`.
`scripts/backfill_brilliant_find_rate.py` re-applies it to stored games from stored data (no engine).
`BRILLIANT_EVAL_MARGIN` is retired. "Why this move?" builds its checklist from the same clauses.

## Consequences

- Measured on the owner's 1,635 games before the backfill (`scripts/benchmark_brilliant_v3.py --you`): 3 Brilliant
  moves in 30,756 (0.01%) under v4 against 6 under v3. Of 493 real sacrifices, 384 fail "sound", 80 come when
  already winning, 20 when already lost and 3 are forced. The looser soundness in one-sided positions mostly
  moves sacrifices onto the "already decided" clauses.
- Brilliant stays a first-class tier and the headline metric (ADR 0001); the band decision (plan 1.3) rests on
  re-measuring Tal under the same rule.
- The You trend marks the week the definition changed.

## Philosophy alignment

Strengthens it: the clauses now ask the questions a player would — was it a real choice, did it keep the game,
was the game still open — instead of a fixed engine margin.

## Gates affected

- `tests/test_brilliant.py` (`TestRuleV4`), `tests/test_brilliant_find_rate.py` (re-judging promotes and demotes),
  `tests/test_explain.py` (checklist numbers in EP).
- `tests/test_golden_analysis.py -m stockfish` passes unchanged.
