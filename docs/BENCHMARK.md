# Sarce — Benchmark plan (Lichess + Chess.com)

**Status:** planned (2026-10-22). Results are recorded here as each part runs, the same way
[VALIDATION.md](./VALIDATION.md) records M4.

Sarce isn't trying to out-engine Chess.com or Lichess. All three run Stockfish. The benchmark answers
four narrower questions:

| # | Question | Part |
| --- | --- | --- |
| 1 | **Trust.** On the same games, do Sarce's evals and move labels broadly agree with Lichess and Chess.com, and is every disagreement explainable? | A, B |
| 2 | **Difference.** What does Sarce see that they don't: sound chaos, squeezed or gave-air moves, real offers? | A |
| 3 | **Cost.** How many CPU-seconds does one game cost? This decides the hosting model ([COMPUTE.md](./COMPUTE.md)). | A, C |
| 4 | **Usefulness.** Do players recognise themselves, and does their style move the way they want? | D |

The goal is to explain differences, not to match. Chess.com's algorithm is closed, Lichess uses a
different labelling model, and Sarce's Brilliant is deliberately stricter (ADR 0004, ADR 0007).

---

## Part A — Lichess comparison (automated)

**Script:** `apps/api/scripts/benchmark_lichess.py` (new). Outputs go to `apps/api/scripts/out/benchmark/`
(gitignored).

### Data sources

| Source | How | Notes |
| --- | --- | --- |
| A player's own games | `GET https://lichess.org/api/games/user/{username}?analysed=true&evals=true&accuracy=true&clocks=true&opening=true&division=true` with `Accept: application/x-ndjson` | Only games that already have a Lichess computer analysis. No token needed. The stream runs at 20 games/s anonymously, 30 with OAuth, 60 for your own games. Make one request at a time. |
| Lichess open database (CC0) | Monthly PGN dumps; analysed games carry `[%eval]` comments | A sample across all ratings that needs no user. Reuses the streaming code in `scripts/validate_chaos.py`. |

### Pipeline

1. Pull N games: 50 for one player, 2,000 for the open-database sample (stratified by 200-point band, like M4).
2. Run each PGN through the normal analysis (Phase 1, Brilliant rules, then the lenses when
   `POSITION_EVALS_ENABLED`). Run it **in memory or against a scratch user**, never a real library.
3. Join per ply:
   - Lichess: eval, judgement (Inaccuracy / Mistake / Blunder where flagged), and accuracy;
   - Sarce: eval, quality, `is_brilliant`, and lens verdicts.
4. Time every stage (Phase 1 search, MultiPV evals, human model, lenses) and count cache hits.

### Metrics

- **Eval agreement:** Pearson and Spearman correlation per ply, plus the median absolute difference.
  Report it in centipawns clipped to ±1000, and in expected points through `ep.cp_to_ep`, so that decided
  positions don't dominate.
- **Label confusion matrix:** Lichess judgement × Sarce quality. For every cell that is more than one step
  apart, list five example positions.
- **Accuracy:** Lichess accuracy vs. a Sarce-side accuracy computed the same way (scatter plus correlation).
- **What Sarce sees that Lichess doesn't:**
  - moves Lichess flags that Sarce scores as `real_chaos` or `calculated_risk`, and the reverse;
  - all Sarce Brilliants (Lichess has no such tier), listed for a human look.
- **Cost:**
  - CPU-seconds per game and per ply, split by stage;
  - cache hit rate;
  - projected CPU-hours for a 3,000-game backfill.

### Done when

This page has the tables for one real player and for the 2,000-game sample, plus a short "why we differ"
list that feeds the Brilliant copy ([REVIEW_2026-10.md](./REVIEW_2026-10.md) §4).

> **Claude Code prompt:** *Read docs/BENCHMARK.md, docs/VALIDATION.md and docs/CHAOS_PLAN.md. Build
> scripts/benchmark_lichess.py on `feat/benchmark-lichess`. Reuse the PGN streaming in validate_chaos.py and
> the existing analysis services. Never write to a real user's library. Start with 20 games from one
> username, then report runtime and CPU per stage before scaling.*

---

## Part B — Chess.com comparison (partly manual)

The Chess.com Published-Data API is read-only and has no Game Review data. It only carries an optional
`accuracies` field when a review was already run. So Chess.com's per-move labels are collected by hand.

1. Review about 30 recent games on Chess.com: mixed results, including at least 10 with a Brilliant or Great move.
2. Record the labels in `apps/api/scripts/out/benchmark/chesscom_labels.csv`:

   ```text
   game_url,ply,san,chesscom_label,chesscom_accuracy_white,chesscom_accuracy_black
   ```

   Shortcut: screenshot the Game Review move list and let Claude vision extract the rows (the app already
   uses Claude vision for screenshot → FEN, `services/ai.py`). Check the extracted rows by eye.
3. `scripts/benchmark_chesscom.py` (new) joins those rows with the synced games and reports:
   - Brilliant precision and recall: Sarce Brilliant against Chess.com Brilliant, and against Brilliant + Great;
   - for each disagreement, which clause failed: offer, eval margin, already winning, find rate, or real offer.
     This list writes the "Why not Brilliant?" copy;
   - accuracy correlation;
   - Miss and Blunder agreement.

**Data handling:** the labels CSV holds game URLs and opponents' moves. Keep it under `scripts/out/`,
which is gitignored. Don't commit it.

---

## Part C — Cost and cheaper analysis

Run on the same 50 games, recording CPU per game and how much the results change against the baseline:

| Option | What changes | Acceptance |
| --- | --- | --- |
| C0 Baseline | Current settings: Phase 1 depth 18; MultiPV 4 → 8 at 1.5M nodes per ply | — |
| C1 Cache pre-load | Load the Lichess evaluation database (CC0) into `position_evals`, converting with `cp_to_ep` | Hit rate per ply; verdicts unchanged where hit |
| C2 Tiered search | A cheap pass on every ply; the full MultiPV only on candidate moments (offers, narrow safe sets, top-N chaos candidates) | Lens verdicts identical on ≥ 95% of moves; Brilliant set identical |
| C3 Recent-first window | Analyse the newest N games first; older history on request | Time to first read |

Keep node limits fixed within each tier, because results must stay reproducible
(`services/position_evals.py`). A mixed-budget search was tried before and dropped for that reason.

---

## Part D — Style pilot (the real test)

- 5–10 players over two weeks, across ratings and time controls (at least 2 bullet, 2 blitz, 1 rapid),
  playing where they normally play.
- After each Summary, ask "Did this read sound like you?" (`games.felt_like_you` already exists) plus one
  free-text line.
- At the end:
  - Did each fingerprint move the way the player said they were aiming for?
  - Would they keep using it?
  - What would they pay for (see [SUSTAINABILITY.md](./SUSTAINABILITY.md))?
- **Proposed success bar:** ≥ 70% "sounds like me" across all reads, and at least half the players would
  keep using it.

---

## Order

1. Part A for one player, cost numbers included.
2. Part C, options C1 and C2 (they need A's numbers).
3. Part B once the 30 labelled games exist.
4. Part D after the first hosted deployment.

## Results

*Not run yet.*
