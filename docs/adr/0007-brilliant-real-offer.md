# ADR 0007 — Brilliant needs a piece genuinely on offer

## Status

Accepted (2026-10-21). Amends [ADR 0004](./0004-brilliant-find-rate.md).

## Context

Brilliant's sacrifice clause used `material_sacrifice`: a moved piece counted as offered whenever *any* legal
reply could land on its square. The "Why this move?" panel showed what that admits — an ordinary developing move
such as 2…Nf6 could pass as a 3-point "sacrifice". The sacrifice library and Home already used a stricter test,
`real_offer` (attacked by something cheaper, or attacked and undefended), so the headline metric was looser than
the screens that explain it.

## Decision

1. A Brilliant move must also pass `real_offer(board, move) ≥ 3` (a minor piece or more genuinely on offer).
   `real_offer` moves to `brilliant.py`; the library imports it from there.
2. Applied at classification (`is_brilliant_move`) and in the post pass (`brilliant_find_rate.py`), which now marks
   style vectors **version 3** / `find-rate-20+real-offer`. `scripts/backfill_brilliant_find_rate.py` re-applies
   both rules to stored games.
3. The "Why this move?" checklist reports the stricter number, so the explanation and the verdict agree.

## Consequences

- Brilliant % falls for players whose "sacrifices" were defended pieces; the You trend shows the change week.
- Fewer false positives in the headline metric; Brilliant stays a first-class tier and the headline (ADR 0001).

## Philosophy alignment

Aligned: Brilliant means a real, sound, hard-to-find offer of material, the Tal idea the app is built around.
