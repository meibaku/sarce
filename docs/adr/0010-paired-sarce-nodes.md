# ADR 0010 — Paired Sarce Nodes: your own machines search for you

## Status

Accepted (2026-10-24, the owner's request). Narrows [ADR 0008](./0008-analysis-off-server.md) for machines the
operator runs and pairs. ADR 0008 stays proposed for players' machines and the browser.

## Context

Analysis is almost all Stockfish searching each position of a game: about three-quarters of a day per thousand
games on one laptop. The owner has a second computer (4 cores, 8 threads, 8 GB) on a direct Ethernet cable. It
loses power now and then. ADR 0008 lets client results reach the shared `position_evals` cache only after the
server re-searches them, to protect other players from forged rows. For a machine the operator runs themselves,
re-searching would cost exactly the work the machine was meant to save.

## Decision

1. **A Sarce Node** (`apps/node`) is an engine worker paired to one Sarce server with a secret token
   (`NODE_TOKEN`). It runs the server's own code (`position_evals.game_lines`, `threats.evaluate_game_threats`,
   the classifier), downloaded from the server it pairs with, so its rows are exactly what the server would
   write. Stockfish gives the same node-limited results in every build of one version. The node uses the
   SSE4.1 build where the CPU has no AVX2, but the same version as the server.
2. **Paired nodes are trusted like the server.** Their engine rows go straight into the shared caches
   (`position_evals`, `position_threats`). Pairing is the operator's act: the token lives in the server's
   environment and is never shown in the app. A node without the token gets nothing.
3. **Nodes never touch the database.** They talk only to the node gateway (`app/node_gateway.py`), which
   checks the token and writes with the service role. Classification, lenses, Brilliant and the human model
   stay on the server: a node fills the engine caches, and the server's own analysis then finds every
   position cached.
4. **The gateway is a separate process** with only the node routes. It binds to the address the operator
   chooses (the cable's address here), so the main API keeps listening on localhost only.
5. **Leases survive power cuts.** A node leases one game at a time (`node_leases`) and sends rows in small
   batches as it goes. A lease with no heartbeat for `LEASE_S` returns its game to the pool, and a restarted
   node re-leases the same game and finds its earlier rows cached. The server's own analysis skips games under
   a live lease.
6. **Updates follow the server.** The gateway serves the code bundle with a version hash. A node whose bundle
   is stale exits, and its runner downloads the new bundle before starting again.

## Consequences

- Throughput adds up across machines. Games a node finished complete on the server in seconds.
- A stolen token could write forged engine rows into the shared cache. It is a single-operator secret, the
  gateway binds to a private link, and the token can be rotated in `.env`.
- Distributing Stockfish carries the GPL source-offer duty already noted in [LEGAL.md](../LEGAL.md). The node
  downloads it from the official release, so Sarce doesn't ship the binary.

## Philosophy alignment

Aligned: local-first, the owner's own machines doing the owner's work, and the rules in one place.

## Gates affected

- `tests/test_nodes.py`: token check, leases (claim, expiry, the server skipping leased games), batched
  writes, the bundle.
- `tests/test_architecture.py` unchanged: routers still never import `chess.engine`. The gateway reaches the
  engine only through services, and runs none itself.
