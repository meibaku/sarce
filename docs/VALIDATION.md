# Chaos Lens validation (M4)

**Status: pilot run done (2,002 positions) — GO.** A full-size run is still to do; see *Results*.

## What is being checked

Whether the chaos score means something: does predicted `P_fail` match how often real players
actually leave the safe set, and does it beat two simple baselines?

| Predictor | Meaning |
| --- | --- |
| `p_fail` | Configured human model: probability of leaving the safe set |
| `p_fail_adjusted` | `p_fail` times the clock multiplier for the replier's clock bucket |
| `baseline_cliff` | EP gap between the best and second-best reply (no findability) |
| `baseline_heuristic` | `P_fail` from the engine-free heuristic model |

The label for each sampled position is whether the reply actually played lost more than `SAFE_TOL`
EP — the same event `P_fail` predicts.

## Method

- Lichess open database (CC0), 1+0 games with clocks only.
- Samples are stratified by 200-point rating band and the replier's clock (`<5s`, `5–15s`, `15s+`).
- Games are split **by game** into a tuning set (70%) and a held-out set (30%).
- The clock multiplier is fit on the tuning set only; every score below is from the held-out set.
- **Go / no-go:** `p_fail_adjusted` must have a lower Brier score than `baseline_cliff` and than the
  heuristic baseline with its own clock multiplier applied (`baseline_heuristic_adjusted`).

## How to run

Needs a local Stockfish (`STOCKFISH_PATH`) and a decompressed Lichess PGN.

```bash
cd apps/api
python -m scripts.validate_chaos path/to/lichess.pgn --positions 2000
```

Start with 2,000 positions to check the pipeline and the runtime, then decide the full sample size
(the plan suggests about 50,000). Outputs go to `apps/api/scripts/out/` (gitignored):

| File | Content |
| --- | --- |
| `chaos_samples.csv` | One row per sampled position |
| `chaos_calibration.csv` | Predicted vs observed rate per band, clock bucket and probability bin |
| `chaos_validation.json` | Brier scores, clock multipliers, the go / no-go flag, runtime |

## Before the result can count

- Select the trained model with `HUMAN_MODEL=maia2` (see [ADR 0002](./adr/0002-human-model.md)). With the
  default heuristic model, `p_fail` and `baseline_heuristic` are the same predictor, so the model
  cannot beat that baseline by construction.
- After a passing run, copy the clock multipliers and any threshold changes into
  `apps/api/app/lenses/config.py` by hand, and record the numbers on this page.

## Results

### Pilot — 10 Oct 2026

The plan's first step: about 2,000 positions to check the pipeline before deciding the full sample.

| | |
| --- | --- |
| Data | First 4.2 MB of `lichess_db_standard_rated_2026-08.pgn.zst`: 4,000 one-minute games with clocks, all from 1 Aug 2026 |
| Sample | 2,002 positions from 337 games; 1,361 tuning, 641 held-out |
| Engine | Stockfish 18, 100,000 nodes, MultiPV 4 (the app default is 1.5M nodes) |
| Human model | `maia2-0.11-blitz` |
| Runtime | 29 minutes on the development machine |

**Brier score on held-out games (lower is better):**

| Predictor | Brier |
| --- | --- |
| `p_fail_adjusted` (Maia-2 + clock multiplier) | **0.175** |
| `p_fail` (Maia-2, unadjusted) | 0.183 |
| `baseline_heuristic_adjusted` | 0.223 |
| `baseline_cliff` | 0.323 |
| `baseline_heuristic` (unadjusted) | 0.458 |

**Verdict: GO** — the adjusted model beats both baselines on games it was not tuned on.

**Calibration on held-out games** (`p_fail_adjusted`, all bands and clocks pooled):

| Predicted | 0.03 | 0.15 | 0.25 | 0.35 | 0.45 | 0.55 | 0.64 | 0.75 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Observed | 0.09 | 0.16 | 0.27 | 0.31 | 0.51 | 0.53 | 0.66 | 0.78 |
| Positions | 169 | 69 | 78 | 51 | 70 | 72 | 64 | 68 |

**Clock multipliers fit on the tuning set:** `<5s` 0.79, `5–15s` 0.76, `15s+` 0.80.

### What the pilot does and does not show

- Predicted and observed failure rates track each other closely across the range, and the model is
  clearly better than the cliff alone or the heuristic.
- **The multipliers are not a clock effect.** They are almost the same in every bucket and all below 1:
  Maia-2 over-predicts failure by about a fifth everywhere. The likely cause is that the script uses
  a fixed MultiPV 4, so a safe fifth-best reply is counted as a predicted failure. Players with under
  5 seconds did **not** fail more often in this sample (30% against 35% with 15 seconds or more).
- The sample is small and narrow: 337 games from the first hours of one day, ratings mostly 1000–2600,
  641 held-out positions, and a search 15 times shallower than the app default.
- Verdict thresholds (`CHAOS_THRESHOLD`, `SAFE_TOL`) were not tuned.

### Openings pass and trap atlas — 10 Oct 2026

A second pass over the same 4,000 games, plies 2–13 only, to give the trap atlas repeated positions
(`--min-ply 2 --max-ply 13`, 50,000 nodes, `maia2-0.11-blitz`): 14,002 positions from 1,343 games in
48 minutes.

- **Validation, again GO:** held-out Brier 0.170 for the adjusted model, 0.198 for the adjusted
  heuristic, 0.258 for the raw cliff. Opening positions only, so this is not an independent check
  of the middlegame.
- **Trap atlas (dry run):** 12,505 distinct position × rating-band pairs, 281 seen at least 3 times,
  **2 traps** where the most-played reply loses at least 0.20 EP:

| Band | Position | Most-played reply | Costs | Seen |
| --- | --- | --- | --- | --- |
| 800–999 | 1. e4 e5 2. Bc4 | 2... f6 | 0.44 EP | 3 |
| 1000–1199 | 1. e4 e5 2. Nf3 Nc6 3. Bc4 | 3... d5 | 0.34 EP | 5 |

Both rest on three to five games, so they are illustrations, not findings. They were **not** written
to `trap_atlas`: no database was reachable from the development machine. A useful atlas needs far
more games per band — hundreds of thousands, not 1,343.

### Before treating chaos numbers as calibrated

1. Rerun with the safe set widened as the app does (`evaluate_position`), and with more nodes.
2. Use a larger sample spread across the month — the plan suggests about 50,000 positions.
3. Decide whether to apply a single calibration factor instead of per-clock multipliers.
4. Only then copy values into `apps/api/app/lenses/config.py` and make Maia-2 the default model.
