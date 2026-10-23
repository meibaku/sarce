# Sarce — Compute strategy

**Status:** proposal (2026-10-22). Part C of the [benchmark](./BENCHMARK.md) supplies the real numbers.
Running analysis outside `apps/api` changes a domain invariant, so it needs
[ADR 0008](./adr/0008-analysis-off-server.md), which is proposed and not yet accepted.

## Where the trajectory drifted

The original spec ([PRODUCT_SPEC.md](./PRODUCT_SPEC.md)) planned a hybrid: Stockfish WASM in the browser
plus native Stockfish on the server. The code today runs **all** analysis in `apps/api`, and AGENTS.md makes
that an invariant ("Stockfish runs server-side only"). "Local-first" now means *self-hostable*, not *the
player's device does the work*. That's fine for one user on a desktop. It is the main cost risk for a hosted
Sarce with many users.

## What a game costs

Per analysed game, the current pipeline runs:

| Stage | Setting | Per |
| --- | --- | --- |
| Shared MultiPV evals (lenses and Phase 1) | `ANALYSIS_NODES=1,500,000`, MultiPV 4, widened to 8 when the safe set isn't closed | every ply, both sides |
| Phase 1 fallback (no shared lines) | depth 18, MultiPV 3, plus two evals after the move | every user ply |
| Prophylaxis threat search | 150,000 nodes, null-move search (`evaluate_game_threats()`) | every uncached position with the user to move |
| Human model (Maia-2) | ~28 ms per position per call (ADR 0002 spike) | each position × Elo rungs |
| Lenses, signals, tagger | pure Python over stored data | negligible |

Stockfish searches roughly a million nodes per second per thread on a modern core. That makes a 1.5M-node
MultiPV search about 1–2 s per ply, and a 60–80-ply bullet game **about 2–5 CPU-minutes**. *This is an
estimate.* Part C of the benchmark replaces it with measured numbers. For scale: M4 used 28.7 worker-hours
for 50,516 positions at only 100,000 nodes, because each sampled position also needed its replies searched.

**Cost model** (fill in after Part C):

```text
CPU-hours per player per month = games per month × CPU-minutes per game × (1 − cache hit rate) / 60
Cost per player per month      = CPU-hours × price per CPU-hour
```

| Example (assumptions, not measurements) | Games/month | CPU-min/game | Cache hits | CPU-hours | At $0.01/CPU-h (dedicated server) | At $0.04/CPU-h (on-demand cloud) |
| --- | --- | --- | --- | --- | --- | --- |
| Regular bullet player | 300 | 3 | 10% | 13.5 | $0.14 | $0.54 |
| Heavy bullet player | 1,500 | 3 | 10% | 67.5 | $0.68 | $2.70 |
| One-off backfill of 3,000 games | 3,000 | 3 | 10% | 135 | $1.35 | $5.40 |

Money is not the bigger problem. **Latency** is: a 3,000-game backfill is about 135 CPU-hours, which is
almost six days on one core. That is why the order of work matters more than the price.

## The layered plan (cheapest first)

```text
1. Shared cache ──► 2. Player's own device ──► 3. Sarce cloud
   (free, instant)     (free to Sarce)            (paid tier / fallback)
```

### 1. Shared position cache

- `position_evals` is already keyed by `(fen_key, nodes)`, so a position analysed for anyone is never searched
  again at the same budget.
- **Known gap:** `engine_version` is stored but neither part of the key nor checked on read, so after a
  Stockfish upgrade the cache keeps serving the old engine's rows. Add the version to the key, or reject
  mismatched rows on read, before the cache is shared widely (the style science plan's data-foundation work).
- **Pre-load the Lichess evaluation database** (CC0 bulk export). Convert cp → EP with `ep.cp_to_ep`. This
  covers openings well and middlegames poorly; Part C measures the hit rate.
- **Lichess cloud-eval** (`/api/cloud-eval`) is for "a few positions here and there". Use it in interactive
  UI, such as the position setter, never in the batch pipeline.
- **Lichess's own analysis:** for Lichess users, games already analysed on Lichess come with per-ply evals
  (`evals=true`). That's enough for Phase 1 labels, but not for the lenses, which need MultiPV.
- **Chess.com:** no per-move analysis is available. Only `accuracies`, when present.

### 2. The player's device

Two options. They aren't exclusive.

**2a. Sarce Node: a desktop helper, Plex-style, but simpler.**

- A small tray app that bundles the existing worker: Python, Stockfish and optionally Maia-2.
- It signs in as the player and **pulls** jobs from `analysis_jobs` over HTTPS. Then it analyses the games and
  posts the results back.
- Plex has to accept connections *into* a home machine. Sarce Node only makes outbound requests, so there's no
  port forwarding and no NAT problem.
- **Idle-aware:** below-normal priority, a configurable CPU cap (default half the threads), pauses on battery
  or when the user is active, and resumes later.
- **Trust:** a player's Node writes only that player's own games, under RLS with their own token, never the
  service-role key. Results from a Node stay scoped to that player. A row enters the shared cache only after the server has
  re-searched that row itself (ADR 0008); sampling a batch isn't enough, because a forger can poison a few
  chosen rows.
- **Packaging risk:** Maia-2 needs PyTorch, a large installer. Options:
  - ship Node with Stockfish only, and let the cloud run the cheap human-model step;
  - export Maia-2 to ONNX (adding onnxruntime is a heavy dependency, so ask first, per AGENTS.md).
- **Licensing:** distributing binaries means distributing Stockfish (GPL-3.0) and Sarce (AGPL-3.0) object
  code. Offer the corresponding source, which a link to the tagged repo plus the Stockfish source covers.
  See [LEGAL.md](./LEGAL.md).

**2b. In the browser (Stockfish WASM).**

- Mature: Lichess runs Stockfish in the browser. Works on phones, which matters because many players have no desktop.
- **Limits:**
  - it only runs while the tab is open;
  - it drains the battery on phones;
  - multi-threaded WASM needs cross-origin isolation headers (COOP/COEP) in `next.config.ts`;
  - the human model would need ONNX Runtime Web (unverified for Maia-2).
- **Best use:** Phase 1 labels and the position setter on demand, not history backfills.

### 3. Sarce cloud

- For players with no device, or who want everything fast. This is the paid tier
  ([SUSTAINABILITY.md](./SUSTAINABILITY.md)).
- Run it on dedicated servers billed at a flat rate, not per-second cloud, since analysis is steady batch work.
- **Queue fairness:**
  - newest games first;
  - the backfill drains in the background;
  - a per-player cap so one 10,000-game import can't starve everyone else.

## Cheaper search without losing the lenses

1. **Recent-first.** On sign-up, analyse the last 20 games at once, then backfill. Time to first read matters
   more than completeness.
2. **Tiered search** (benchmark C2):
   - a cheap fixed-node pass on every ply;
   - the full 1.5M-node MultiPV only where a lens can fire: real offers, positions with ≤ 3 safe replies,
     winning/losing bands for squeeze and swindle, and top chaos candidates.
3. **Skip decided positions** for the expensive pass. The chaos lens already ignores EP outside 0.10–0.90.
4. **Opponent plies:** the lenses need the position after each user move (the opponent's choices) but not
   always a deep search of every opponent move. Measure what can be dropped.

## Decision needed

Accept or reject [ADR 0008](./adr/0008-analysis-off-server.md) after benchmark Part C. Until then, nothing
here changes code.
