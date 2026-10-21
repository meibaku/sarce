# Chaos Lens validation (M4)

**Status: full-size run done — GO on 50,516 positions from twelve months.** See *Results*; the two earlier,
smaller runs are kept below it for the record.

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

### Full-size run — 10–11 Oct 2026

The plan's target: about 50,000 positions, stratified by rating band and the replier's clock.

| | |
| --- | --- |
| Data | The first 1,500 one-minute games with clocks from each of twelve monthly Lichess files, September 2025 to August 2026 |
| Sample | **50,516 positions from 3,218 games**; 34,429 tuning, 16,087 held-out (split by game) |
| Engine | Stockfish 18, 100,000 nodes, MultiPV 4 widened to 8 when the safe set was not closed |
| Human model | `maia2-0.11-blitz` |
| Compute | 28.7 worker-hours, about 7 hours on the clock with four workers |

**Brier score on held-out games (lower is better):**

| Predictor | Brier |
| --- | --- |
| `p_fail_adjusted` (Maia-2 + clock multiplier) | **0.155** |
| `p_fail` (Maia-2, unadjusted) | 0.156 |
| `baseline_heuristic_adjusted` | 0.218 |
| `baseline_cliff` | 0.335 |
| `baseline_heuristic` (unadjusted) | 0.414 |

**Verdict: GO** — overall, and separately in every one of the twelve months (0.145–0.168 against
0.212–0.224 for the adjusted heuristic).

**Calibration on the 16,087 held-out positions** (`p_fail_adjusted`):

| Predicted | 0.03 | 0.15 | 0.25 | 0.35 | 0.45 | 0.55 | 0.65 | 0.75 | 0.85 | 0.93 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Observed | 0.06 | 0.17 | 0.25 | 0.35 | 0.44 | 0.53 | 0.62 | 0.71 | 0.83 | 0.94 |
| Positions | 4,042 | 2,023 | 1,614 | 1,340 | 1,260 | 1,161 | 1,139 | 1,197 | 1,402 | 909 |

**Clock, all 50,516 positions:**

| Replier's clock | Positions | Observed failure | Maia-2 predicted | Multiplier (tuning set) | Range across months |
| --- | --- | --- | --- | --- | --- |
| under 5 s | 2,426 | 0.357 | 0.300 | **1.23** | 1.05–1.40 |
| 5–15 s | 7,255 | 0.365 | 0.366 | **0.98** | 0.88–1.07 |
| 15 s or more | 40,835 | 0.392 | 0.421 | **0.93** | 0.87–0.96 |

What this settles:

- **The score means something.** Predicted and observed failure rates agree within a few points across
  the whole range, on games the multipliers were not fit to.
- **The clock effect is real and stable in direction:** under 5 seconds the multiplier was above 1 in
  all twelve months. `CLOCK_MULTIPLIERS["maia2"]` in `apps/api/app/lenses/config.py` now holds these
  values, replacing the four-month estimates.
- **The trap atlas needs a different sample.** The builder found no traps in these 50,516 positions:
  they start at ply 8, where positions rarely repeat. The atlas needs an openings-only pass over far
  more games (the openings pass below found two thin ones in 1,343 games).

Remaining limits:

- Each month is represented by the games at the very start of its file (its first hours), not a
  spread across the month.
- 100,000 nodes per search, against the app's default of 1.5 million.
- One-minute games only; no other time control was tested.
- `CHAOS_THRESHOLD` and `SAFE_TOL` are still the starting values. Validation shows `P_fail` is
  calibrated; it does not say where "worth flagging" begins.

### Trap atlas — openings pass over twelve months

An openings-only pass (plies 2–11, 50,000 nodes, `maia2-0.11-blitz`) over the same twelve monthly
samples used for the full run. The pass is complete for three of the four worker batches; the fourth was stopped part-way (about 4,850 of its 7,000 games) and its positions so far are included.

| | |
| --- | --- |
| Games | 18,122 one-minute games |
| Positions | 162,983 |
| Traps | **277** positions where the most-played reply at a rating band loses at least 0.20 EP and the position was seen at least 3 times |
| Seen 5 or more times | 77 |

The traps are in `apps/api/data/trap_atlas.json`. Loading them needs the database:

```bash
cd apps/api
python -m scripts.build_trap_atlas --load data/trap_atlas.json
```

How far to trust it: most traps were seen only three or four times at their band (77 were seen five
or more times, 8 ten or more), and the search was shallow (50,000 nodes), so a trap whose cost is close
to the 0.20 EP threshold may be search noise. Each one is a
lead worth looking at, not a measured rate. The 1400–1999 bands hold most of them because that is
where the sample has the most games. The atlas keeps positions and counts only — no players or games.

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

### Four-month run with widened safe sets — 10 Oct 2026

The pilot's main caveat was the fixed MultiPV 4. The sampler now widens the search the way the app
does, and this run draws from four monthly files instead of one.

| | |
| --- | --- |
| Data | The first 1,500–4,000 one-minute games of the March, May, July and August 2026 Lichess files |
| Sample | 4,820 positions from 411 games; 3,312 tuning, 1,508 held-out |
| Engine | Stockfish 18, 100,000 nodes, MultiPV 4 widened to 8 when the safe set was not closed |
| Human model | `maia2-0.11-blitz` |
| Runtime | About 65 minutes per month, run four at a time |

**Brier score on held-out games (lower is better):**

| Predictor | Brier |
| --- | --- |
| `p_fail_adjusted` (Maia-2 + clock multiplier) | **0.169** |
| `p_fail` (Maia-2, unadjusted) | 0.170 |
| `baseline_heuristic_adjusted` | 0.220 |
| `baseline_cliff` | 0.340 |
| `baseline_heuristic` (unadjusted) | 0.401 |

**Verdict: GO**, combined and in each of the four months separately (0.156–0.200 against 0.215–0.231
for the adjusted heuristic).

**Calibration on held-out games** (`p_fail_adjusted`):

| Predicted | 0.03 | 0.15 | 0.25 | 0.35 | 0.45 | 0.54 | 0.65 | 0.75 | 0.85 | 0.96 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Observed | 0.08 | 0.24 | 0.25 | 0.31 | 0.42 | 0.50 | 0.71 | 0.67 | 0.82 | 0.90 |
| Positions | 376 | 151 | 161 | 126 | 138 | 136 | 104 | 109 | 121 | 86 |

**Clock, all 4,820 positions:**

| Replier's clock | Positions | Observed failure | Maia-2 predicted | Multiplier (tuning set) |
| --- | --- | --- | --- | --- |
| under 5 s | 384 | 0.365 | 0.297 | 1.28 |
| 5–15 s | 1,122 | 0.406 | 0.384 | 1.03 |
| 15 s or more | 3,314 | 0.377 | 0.415 | 0.91 |

What changed from the pilot:

- **The uniform over-prediction is gone.** Overall predicted failure is 0.399 against 0.383 observed,
  so the pilot's flat 0.78 was the truncation artefact it looked like.
- **A clock effect appears, in the expected direction:** with under 5 seconds players fail about a
  quarter more often than Maia-2 predicts; with plenty of time, slightly less. The under-5-second
  figure rests on 384 positions and ranged from 0.80 to 1.47 across the four months, so it is
  provisional.
- These multipliers are now in `apps/api/app/lenses/config.py` (`CLOCK_MULTIPLIERS["maia2"]`) and
  applied to `P_fail` by the lenses when the model is Maia-2 and the game has clocks.

Still short of the plan's target: 4,820 positions, not 50,000; each month is represented by its first
hours only; the search is 15 times shallower than the app default; verdict thresholds are untuned.

### Still to do

1. Tune `CHAOS_THRESHOLD` and `SAFE_TOL` against how flagged moves read in real game reviews.
2. Run an openings-only pass over a much larger set of games to fill the trap atlas.
3. If other time controls matter, repeat the clock fit for them; the multipliers here are for 1+0.
