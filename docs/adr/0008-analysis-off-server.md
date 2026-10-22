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
   - every result written from outside `apps/api` goes through an authenticated API endpoint as the player,
     under RLS, never with the service-role key;
   - classification and lens rules stay in one place: `apps/api/app/services` and `app/lenses`. Clients
     return raw engine lines, and the server applies the rules.
3. Results from clients never enter the shared `position_evals` cache unless they pass a server spot check.
4. The Node and the browser engine are opt-in. Self-hosting and the cloud tier keep working without them.

## Consequences

### Positive

- The free tier costs Sarce close to nothing in compute.
- Faster backfills for players with a desktop.
- The rules stay server-side, so all clients get the same Brilliant and lens verdicts.

### Negative / trade-offs

- A new distributable (installer, updates, code signing) and a new attack surface: forged results. Forged
  results only affect the forger's own data, plus the cache spot check.
- GPL/AGPL source-offer duties for distributed binaries ([LEGAL.md](../LEGAL.md)).
- Maia-2 on the client means a heavy dependency (PyTorch or ONNX Runtime), so ask before adding it.

## Philosophy alignment

Aligned. Local-first and self-hostable stay first-class; the player's own machine does their own work.
Nothing changes in what Brilliant or the lenses mean.
