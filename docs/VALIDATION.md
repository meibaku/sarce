# Chaos Lens validation (M4)

**Status: not run yet.** This page describes the check and how to run it. No results are recorded
here until a real run has produced them.

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

- A trained human model must be selected (see [ADR 0002](./adr/0002-human-model.md)). With the
  default heuristic model, `p_fail` and `baseline_heuristic` are the same predictor, so the model
  cannot beat that baseline by construction.
- After a passing run, copy the clock multipliers and any threshold changes into
  `apps/api/app/lenses/config.py` by hand, and record the numbers on this page.

## Results

_None yet._
