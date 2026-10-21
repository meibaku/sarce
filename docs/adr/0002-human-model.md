# ADR 0002 — Human move model for the Chaos Lens

## Status

Accepted for Maia-2 as an **optional** model — adapter merged, off by default, not in the base
requirements. Adopted under the maintainer's instruction to implement the recommendations; revert by
removing `maia_model.py` and `requirements-maia.txt`. The default is `HUMAN_MODEL=auto`: Maia-2 wherever the optional package is installed, the heuristic elsewhere.

## Context

The Chaos Lens needs `P(move | position, Elo)`: how likely a human of a given rating is to find each
reply. [CHAOS_PLAN.md](../CHAOS_PLAN.md) (M2) calls for a rating-conditioned model such as Maia-2 or
Maia-3 rather than hand-made heuristics, chosen after a half-day spike.

The spike has now been run for Maia-2 (see *Spike findings*). Adopting a trained model adds a heavy
dependency, which the plan's ground rule 8 reserves for the maintainer.

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

## Spike findings (10 Oct 2026)

Run in an isolated virtual environment outside the project, on the development machine
(Windows 11, CPU only, 4 PyTorch threads). Nothing was added to the app's dependencies.

### Maia-2 (`maia2` 0.11.0 from PyPI) — measured

| Question | Result |
| --- | --- |
| Licence | MIT (package metadata and bundled LICENSE) |
| Install | `pip install maia2` — 17 minutes on this connection, 1.6 GB on disk, pulls `torch` 2.8 (CPU) and `pandas` |
| Python | Requires >= 3.10, < 3.13 |
| Weights | 280 MB, fetched from Google Drive on first use, checked against a pinned SHA-256, loaded with `weights_only=True` |
| Load time | About 2 s once the weights are cached |
| Speed | **27.8 ms per position** over 200 positions; all six ladder Elos for one position in about 150 ms |
| Full distribution | Yes — a probability for every legal move in 200 / 200 positions, each summing to 1 |
| Rating conditioning | Separate Elo for the mover and the opponent. 2000 and 2400 gave identical output, so the top of our ladder collapses |
| Clock | Not an input. Trained on blitz (a rapid checkpoint also exists) |

Sanity check on a position everyone knows — after 1. e4 e5 2. Qh5 Nc6 3. Bc4, Black must stop Qxf7#:

| Elo | Maia-2 P(safe reply) | Maia-2 P(Nf6??) | Interim heuristic P(safe reply) |
| --- | --- | --- | --- |
| 800 | 0.77 | 0.090 | 0.15 |
| 1200 | 0.90 | 0.043 | — |
| 1600 | 0.93 | 0.025 | 0.15 |
| 2000 | 0.94 | 0.019 | — |
| 2400 | 0.94 | 0.019 | 0.15 |

Maia-2 gives a believable curve (about 1 in 4 players at 800 go wrong, about 1 in 17 at 2000). The
heuristic says 85% miss at every rating, which matches what the smoke run showed: it over-triggers
and must not be used for anything user-facing.

### Maia-3 — read, **not** measured

From the project's README (github.com/CSSLab/maia3); it was not installed or timed.

| Question | What the README says |
| --- | --- |
| Licence | **AGPL-3.0** |
| Install | From source (`git clone` + `pip install .`); weights from Hugging Face on first run |
| Form | A UCI engine (`maia3-5m`); 5M, 23M and 79M models |
| Rating conditioning | `Elo`, `SelfElo`, `OppoElo` UCI options |
| Full distribution | Not stated — MultiPV lines show "likely human moves" |
| Clock | Not mentioned |

### Recommendation

**Maia-2.** Its MIT licence fits this repository (MIT is compatible with Sarce's AGPL-3.0, ADR 0006), it returns the full distribution the lenses need
in a single call, and it is fast enough: roughly 5 s of model time for an 80-ply game across the
ladder, against about 4 s per position for Stockfish.

Maia-3 could only be used as a separate UCI process, the way Stockfish is, and its AGPL terms would
need a deliberate decision before any hosted deployment. It is also unconfirmed that its UCI output
gives a probability for every legal move.

### How Maia-2 is integrated

- `apps/api/app/services/maia_model.py` — `Maia2HumanModel`, selected with `HUMAN_MODEL=maia2`. The
  package is imported lazily, so the API and CI run without it.
- `apps/api/requirements-maia.txt` — the optional install (about 1.6 GB with PyTorch). It is **not** in
  `requirements.txt`.
- `tests/test_architecture.py` bans direct ML imports in `app/`; the adapter imports only `maia2`, so
  that gate is unchanged. Move classification is still rule-based.
- Cache rows are versioned `maia2-0.11-blitz`, separate from `heuristic-1`.
- Default `HUMAN_MODEL=auto` (added after the M4 validation passed): Maia-2 if installed, otherwise the
  heuristic, so no installation is forced to carry PyTorch.
- Still open: dropping the redundant 2400 rung of the ladder.

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
