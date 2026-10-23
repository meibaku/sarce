# ADR 0008 — Analysis may run outside the API server

## Status

Proposed (2026-10-22). Decide after benchmark Part C ([BENCHMARK.md](../BENCHMARK.md)) has measured the
CPU cost per game.

## Context

AGENTS.md makes "Stockfish runs server-side only (`apps/api`)" a domain invariant. That kept Phase 1 simple.
A hosted Sarce, though, pays for every search, and a large history takes days of CPU per player
([COMPUTE.md](../COMPUTE.md)). The original product spec planned client-side Stockfish (WASM) next to the
server.

## Decision (proposed)

1. Engine analysis may also run in two trusted-for-self places:
   - **Sarce Node**: a desktop helper that pulls the player's own jobs from `analysis_jobs`;
   - **the browser**: Stockfish WASM, for on-demand Phase 1 and the position setter.
2. The invariant is narrowed, not dropped:
   - routers still never import `chess.engine`;
   - clients never write to the database directly. They submit results to an authenticated `apps/api`
     endpoint as the player; the API checks the job belongs to that player and writes the player's own rows
     server-side. `position_evals` keeps its current RLS (authenticated read, service-role write), so no
     client-facing insert policy is added;
   - classification and lens rules stay in one place: `apps/api/app/services` and `app/lenses`. Clients
     return raw engine lines, and the server applies the rules.
3. Client results stay **scoped to the submitting player**. A row enters the shared `position_evals` cache
   only after the server has re-searched that row itself. Sampling a batch is not enough: a forger can corrupt
   a few chosen rows and expect none to be sampled, and a poisoned shared row reaches every player who meets
   that position.
4. The Node and the browser engine are opt-in. Self-hosting and the cloud tier keep working without them.

## Consequences

### Positive

- The free tier costs Sarce close to nothing in compute.
- Faster backfills for players with a desktop.
- The rules stay server-side, so all clients get the same Brilliant and lens verdicts.

### Negative / trade-offs

- A new distributable (installer, updates, code signing) and a new attack surface: forged results. Because
  client rows stay player-scoped until the server verifies them one by one, a forgery only affects the
  forger's own data. The cost is that client work only fills the shared cache at the server's verify rate.
- GPL/AGPL source-offer duties for distributed binaries ([LEGAL.md](../LEGAL.md)).
- Maia-2 on the client means a heavy dependency (PyTorch or ONNX Runtime), so ask before adding it.

## Philosophy alignment

Aligned. Local-first and self-hostable stay first-class; the player's own machine does their own work.
Nothing changes in what Brilliant or the lenses mean.
