# Sarce — Style Science Plan (for Claude Code)

**Status:** planned (2026-10-23). Nothing here has started.

**What this is:** the milestone plan that follows the chaos plan ([CHAOS_PLAN.md](./CHAOS_PLAN.md), M0–M8, all
merged). It turns the October research report and [REVIEW_2026-10.md](./REVIEW_2026-10.md) (findings F1–F11)
into ordered, reviewable PRs, each with a Claude Code prompt.

**One-line goal:** *the engine shows truth; Maia shows humans; Sarce shows **you**, with numbers honest enough
to publish.*

Related: [BENCHMARK.md](./BENCHMARK.md) · [COMPUTE.md](./COMPUTE.md) · [VALIDATION.md](./VALIDATION.md) ·
[LEGAL.md](./LEGAL.md)

---

## Status at a glance

| Milestone | Theme | Horizon | Status |
| --- | --- | --- | --- |
| S0 | Planning and spikes: decide before building | Weeks 1–2 | Planned |
| S1 | Quick validity fixes (F2, F5, F11) | Weeks 1–2 | Planned |
| S2 | Data foundation: cache key, versioning, raw vs derived | Month 1 | Planned |
| S3 | Rating conversion (F1) | Month 1 | Planned |
| S4 | Human model upgrade: Maia-3, if the spike passes | Month 2 | Planned |
| S5 | One unit: a rating- and time-control-aware EP model | Month 2 | Planned |
| S6 | Population reference and percentiles | Month 2–3 | Planned |
| S7 | Honest uncertainty: shrinkage, intervals, read states | Month 3 | Planned |
| S8 | Trait science: factor analysis, reliability, known groups → 4–6 constructs | Month 3–4 | Planned |
| S9 | Brilliant recalibration by rating band | Month 4 | Planned |
| S10 | New lenses: Originality (surprisal × EP), difficulty-adjusted performance | Month 4–5 | Planned |
| S11 | Clock hazard and session/tilt lens | Month 5–6 | Planned |
| S12 | Compute at scale: tiered search, cache seeding, Sarce Node beta | Months 2–6 (parallel) | Planned |
| S13 | Grounded commentary: LLM paraphrases verified facts only | Month 6 | Planned |
| S14 | Personal style models: embeddings, "distance to Tal", style timeline | Months 7–12 | Planned |
| S15 | Opening simulation vs Maia, and an open Sarce Style Benchmark | Months 9–12 | Planned |

Benchmark Parts A–D ([BENCHMARK.md](./BENCHMARK.md)) run alongside: Part A before S4, Part C feeds S12, Part D
after the first deployment.

---

## Ground rules for Claude Code

The chaos plan's eight ground rules still apply: never break Phase 1, one milestone per PR, lenses are pure
functions, EP not centipawns, `go nodes N`, post-game only, new migrations with RLS, and ask before a heavy
dependency. Add these:

9. **Plan first, then build.** Every milestone starts in plan mode. Claude Code writes the plan (files, schema,
   tests, risks) and **stops for approval**. Each milestone below has two prompts: *Plan* and *Build*.
10. **Validate before it reaches the UI.** A new metric ships behind a flag until it has a validation entry in
    VALIDATION.md (calibration for probabilities; reliability and known groups for traits).
11. **Version everything.** Each derived row carries `metric_version`, `model_version` and `engine_config`. Never
    overwrite a stored definition: backfill under the new version and compare like with like.
12. **Split by player, then by time.** Held-out sets are split by player (no leakage), plus a temporal split
    (fit before month M, test after).
13. **Count events, not games.** Minimum samples are stated per metric, as eligible moves or positions.
14. **No causal claims in copy.** The time and tilt evidence is observational. Coaching says "tends to", never
    "causes".
15. **Privacy:** population statistics come from public CC0 Lichess data first. User-derived aggregates need a
    minimum cell size. Style embeddings are never exposed publicly, because stylometry can re-identify people.
16. **Docs are part of done:** CHANGELOG, this file's status table, and an ADR when an invariant changes.

### How each milestone runs (the plan-to-plan loop)

```text
1. Plan prompt  → Claude Code reads the listed docs and code, writes a plan, stops.
2. You approve or adjust the plan (scope, thresholds, dependencies).
3. Build prompt → a branch off staging, tests first, small commits, PR with the template.
4. Validation   → results recorded in VALIDATION.md; the flag is lifted only if the bar is met.
5. Status       → tick the row above; note open decisions below.
```

---

## S0 — Planning and spikes (decide before building)

**Goal:** settle the decisions that later milestones depend on, using small measured spikes. No product code
changes.

Tasks:

1. **Maia-3 spike.** ADR 0002 recorded Maia-3 as "read, not measured". Now measure it:
   - install it in `scripts/`;
   - time 200 positions;
   - check whether its UCI output gives a probability for **every** legal move (the lenses need the full
     distribution);
   - compare the Elo, SelfElo and OppoElo conditioning;
   - check the licence (AGPL-3.0, same as Sarce, run as a separate process).

   Write the results into ADR 0009 (Proposed).
2. **Rating-conversion sources:**
   - list the candidate Chess.com↔Lichess anchors, such as ChessGoals' crowd table (about ±70 error, N = 1,935);
   - plan the opt-in "link both accounts" data collection;
   - draft ADR 0010.
3. **The EP model's scope:**
   - decide which Lichess months, which time controls, and which rating bands (200 points);
   - draft ADR 0011: classification by EP loss, retiring the centipawn thresholds.
4. **Metric registry:** list every derived number (Brilliant, the nine traits, the lens verdicts), with its unit,
   inputs, current version and validation status. This is the checklist for S2 and S8.
5. **Population sample spec:**
   - one recent month per time control;
   - stratified by band;
   - target sizes per cell;
   - storage format (Parquet, partitioned by month).

**Done when:** ADRs 0009–0011 exist as Proposed with measured numbers, `docs/METRICS.md` (the registry) exists,
and you've made the calls listed under *Open decisions*.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S0), docs/adr/0002-human-model.md, docs/REVIEW_2026-10.md
> and apps/api/app/services/human_model.py. Plan the S0 spikes only: what each script measures, where it lives
> under apps/api/scripts/, runtime budget, and what each ADR must answer. Don't write code yet. Stop for my
> approval.*
>
> **Build prompt:** *Run the approved S0 spikes on `chore/s0-spikes`. Write the Maia-3 findings to ADR 0009
> (Proposed), rating-conversion sources to ADR 0010 (Proposed), the EP scope to ADR 0011 (Proposed), and a
> metric registry to docs/METRICS.md. No product code changes. Report numbers, not opinions.*

---

## S1 — Quick validity fixes

**Goal:** fix the review findings that are small and clearly wrong, before the larger refactors.

Tasks:

- **F2:** add a `real_sacrifice` signal (`real_offer ≥ 3`, with pawn offers as their own bucket). Base the
  Sacrifice trait on it. Bump `style_vectors.version`. Rescore the three references.
- **F5.2:** exclude lost positions from Brilliant symmetrically, with the same decided band as chaos
  (`DECIDED_LOW/HIGH` in EP).
- **F5.1:** decide what "not forced" means (an only-move sacrifice: Brilliant or not?), record it in an ADR, and
  test it.
- **F11:** the find-rate rule uses the mover's own rating, at the rung rounded to 100 that `elo_ladder` already
  adds, not the opponent's rating at 400-point rungs.

**Done when:** Tal ranks at or above Morphy on Sacrifice, the golden tests pass, and the backfill script
re-applies the rules.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S1), docs/REVIEW_2026-10.md F2/F5/F11,
> services/brilliant.py, services/move_signals.py, services/brilliant_find_rate.py and services/you.py. Plan
> the four fixes: exact rule changes, which tests to write first, the style-vector version bump and the
> backfill. Stop for approval.*
>
> **Build prompt:** *Implement the approved S1 plan on `fix/s1-validity`. Tests first. Bump style_vectors.version.
> Rescore reference_axes.json and report before/after for Tal, Shirov and Morphy.*

---

## S2 — Data foundation

**Goal:** the cache, versioning and storage that every later milestone relies on.

Tasks:

1. **Cache key:** `position_evals` uses `(fen_key, nodes)` as its primary key. `engine_version` is stored, but
   it isn't part of the key, so a Stockfish upgrade would silently mix evaluations from different engines. Make
   the key `(fen_key, engine_version, network, nodes, multipv)` in a new migration, with the old rows migrated
   under their recorded version.
2. **Raw vs derived:**
   - raw per-ply data stays immutable (evals, WDL, MultiPV, Maia top-k plus entropy, clocks);
   - derived rows (`move_lens_scores`, style vectors, traits) carry `metric_version`, `model_version` and
     `engine_config`;
   - trend queries filter to one version.
3. **Store entropy and the top-k** of the human-model distribution per position. S10 needs them, and storing them
   now avoids re-running Maia later.
4. **Search-depth trace:** record the eval at a few fixed node checkpoints in the search you already run (for
   example 100k, 400k and 1.5M). The Guid–Bratko depth-instability measure in S10 needs them, and they come
   almost free.
5. **Bulk storage:** population and benchmark data (millions of plies) go to Parquet partitioned by month, under
   object storage or `scripts/out/`, not Postgres. Postgres keeps users and derived metrics.
6. **Provenance:** every cached eval records where it came from: `sarce`, `lichess-evaldb`, `node:<id>` or
   `browser`.

**Done when:** the migrations are applied, old data is readable, a version filter is used by the You trend, and
METRICS.md lists every derived number's version.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S2), docs/COMPUTE.md,
> supabase/migrations/20261010000000_position_evals.sql, services/position_evals.py, services/lens_service.py
> and docs/METRICS.md. Plan the cache-key migration (how old rows are kept), the versioning columns and where
> each is written, and what the trend queries must filter on. Flag every query that would mix versions. Stop
> for approval.*
>
> **Build prompt:** *Implement the approved S2 plan on `feat/s2-data-foundation`. New migrations only, RLS on
> new tables. Add tests proving that a Stockfish version change misses the cache, and that trends never mix
> metric versions.*

---

## S3 — Rating conversion (F1)

**Goal:** every rating that meets a Lichess-trained model is first converted to Lichess-equivalent, by platform
and time control.

Tasks:

- `rating_to_model_elo(source, time_control, rating) -> (elo, uncertainty)`, in one module, versioned.
- **Initial table** from the S0 sources, interpolated by band. Large, level-dependent offsets are expected: for
  example Chess.com blitz 800 ≈ Lichess 1290, 1200 ≈ 1555, 1700 ≈ 1885, per ChessGoals (±70).
- **Refit later** from opt-in players who link both accounts (recorded in the S0 plan).
- Used everywhere a rating meets the human model: chaos, the find rate, the trap atlas band, chaos map, scouting.
- Bump the lens and style-vector versions, then backfill.

**Done when:** a Chess.com game's chaos and find-rate use the converted rating, and benchmark Part B shows
whether Chess.com-game calibration improved. Re-run the M4-style check on a sample of imported Chess.com
games: compare predicted with observed opponent failure.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S3), docs/adr/0010 (Proposed), services/human_model.py,
> lenses/chaos.py and services/brilliant_find_rate.py. List every place a rating meets the human model. Plan
> the conversion function, its table format and versioning, and a calibration check on Chess.com games. Stop
> for approval.*
>
> **Build prompt:** *Implement the approved S3 plan on `feat/s3-rating-conversion`. Accept ADR 0010. Tests for
> each platform and time control and for unknown ratings. Bump versions, add a backfill command, and report how
> chaos scores shift on a sample of Chess.com games.*

---

## S4 — Human model upgrade (Maia-3, if S0 passes)

**Goal:** a better human policy improves every lens at once. Maia-3 reports 57.1% move matching (ICLR 2026),
and the Maia-2 repository now recommends Maia-3 for new projects.

**Gate:** only if the S0 spike shows a full move distribution (or a workable approximation), acceptable speed on
CPU, and that the AGPL process boundary is fine (ADR 0009).

Tasks:

- A `Maia3HumanModel` behind the existing `HumanModel` interface, running as a separate UCI process like
  Stockfish, and selected by `HUMAN_MODEL`.
- New `model_version`, so the `human_probs` cache entries stay separate.
- **Re-run M4** (`validate_chaos.py`) on the same 50,516-position design with Maia-3, and refit the clock
  multipliers. Ship only if the held-out Brier score is at least as good as Maia-2's 0.155.
- Extend validation to **3+0 and 10+0**, so blitz and rapid lose the "uncalibrated" badge.

**Done when:** VALIDATION.md has the Maia-3 results by time control, and the default model follows the result.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S4), docs/adr/0009 (Proposed), services/human_model.py,
> services/maia_model.py, scripts/validate_chaos.py and docs/VALIDATION.md. Plan a Maia-3 adapter as a UCI
> process, cache separation, and the validation runs (1+0, 3+0, 10+0) with runtime estimates. Stop for
> approval.*
>
> **Build prompt:** *Implement the approved S4 plan on `feat/s4-maia3`. Keep Maia-2 as the default until
> validation passes. Run the 2,000-position pilot first and report, then the full runs I approve. Record
> everything in VALIDATION.md.*

---

## S5 — One unit: a rating- and time-control-aware EP model

**Goal:** one expected-points scale for classification and all lenses (F5.3, F8). Chess.com's Classification V2
already uses a rating-aware expected-points model; Sarce fits its own on open data.

Tasks:

- **Fit EP** = P(win) + ½P(draw) as a function of eval, rating band and time control, using Lichess games that
  have evals (about 6% of games) plus results and clocks. Start with logistic or ordinal regression, and
  calibrate it (reliability diagram, isotonic correction if needed).
- **Classification by EP loss** (ADR 0011). Cut-offs are fitted so the tier shares stay sensible per band, and
  the centipawn `THRESHOLDS` are retired.
- **Lens thresholds in EP:** squeeze, swindle, clock, prophylaxis.
- Bump the style-vector version and backfill.

**Done when:** EP calibration is within ±3 points across bins on held-out games, every threshold in
`lenses/config.py` is EP, and benchmark Part A label agreement is recorded before and after.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S5), docs/adr/0011 (Proposed), services/ep.py,
> services/move_classifier.py and lenses/config.py. Plan the EP fit (data, features, model, validation split by
> player and time), the new classification cut-offs, and the threshold conversions per lens. Show what changes
> for users. Stop for approval.*
>
> **Build prompt:** *Implement the approved S5 plan on `feat/s5-ep-model`. Fitting script under
> apps/api/scripts/, coefficients in a versioned data file, tests for monotonicity and calibration, golden tests
> updated deliberately. Accept ADR 0011.*

---

## S6 — Population reference and percentiles

**Goal:** a trait means something only against people like you (F10).

Tasks:

- Build the population sample from the S0 spec: a recent Lichess month per time control, stratified by
  200-point band, run through the *same* pipeline (S2–S5), stored as Parquet. Like the trap atlas, it keeps
  positions and counts only, no names.
- Compute each trait's distribution per band × time control, and store percentile tables (versioned).
- The API returns raw values and percentiles. The UI uses percentiles ("more than 80% of 1500 bullet players").

**Done when:** every trait on You has a percentile with its population version, and a methods note explains
where the reference comes from.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S6), scripts/validate_chaos.py (streaming),
> services/you.py and docs/METRICS.md. Plan the population run (sample sizes per cell, runtime, storage) and
> the percentile tables' format and versioning. Stop for approval.*
>
> **Build prompt:** *Implement the approved S6 plan on `feat/s6-population`. Pilot one band and time control
> first and report runtime. Percentile tables go in apps/api/data/ with a version; the API exposes percentiles
> next to raw values.*

---

## S7 — Honest uncertainty

**Goal:** fix the five-game problem (F4) without losing the coaching feel.

Tasks:

- **Hierarchical shrinkage:** each player's rate is shrunk toward their band × time-control prior from S6
  (beta-binomial for rates; normal–normal for means), with a posterior interval.
- **Read states** instead of ± by default: *early read* → *taking shape* → *clear signal*, decided by the
  interval width. The interval is shown on tap, and as a shaded band on the axes.
- **Trends:** a rolling window of about 20 games. "Up" or "down" only when the windows' intervals separate.
- **Positive framing:** for example, "3 more sharp games to confirm your attacking streak."
- **Optional:** Glicko-style per-trait ratings ("Sacrifice 1640 ± 90") as a later display experiment.

**Done when:** no trait shows a bare number before it's settled, and `MIN_GAMES` is replaced by per-metric event
thresholds (set in S8).

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S7), services/home.py, services/you.py, the You and Home
> components (web and mobile) and docs/DESIGN.md. Plan the shrinkage model, the read-state thresholds, the API
> fields, and the UI changes on both platforms, with copy that passes philosophy-check. Stop for approval.*
>
> **Build prompt:** *Implement the approved S7 plan on `feat/s7-uncertainty`. Pure-function stats module with
> tests (known beta-binomial cases), API fields, then web and mobile UI. Update the design notes.*

---

## S8 — Trait science: from nine traits to four–six constructs

**Goal:** keep only traits that are distinct, reliable and about style rather than strength.

Tasks:

1. **Factor analysis** of the nine traits on the S6 population: correlation matrix, then exploratory factor
   analysis. Merge traits that load on one factor. Expected: chaos, swindle and fight merge, and squeeze, grip
   and survival merge. Test this, don't assume it.
2. **Reliability:** split-half (odd vs even games) and test-retest (month t vs t+1). Target ≥ 0.7. Use
   Spearman–Brown to set each construct's unlock threshold in events.
3. **Known groups, on identical pipelines** (the fix for F3):
   - Tal and Shirov vs Petrosian and Karpov, at least 200 games each, same engine settings and same model
     (Maia-3 at a high band, flagged as out of distribution for classical games);
   - plus Lichess groups that differ in openings or in self-reported style (the pilot).
4. **Discriminant check:** after shrinkage and percentiles, a style construct should correlate only weakly with
   rating. If one mostly tracks rating, it's a skill measure. Move it out of the "style" panel.
5. **Rebuild the reference dots** from step 3, with intervals, labelled "classical".
6. Bump the style-vector version. Update the You screen to the surviving constructs.

**Done when:** VALIDATION.md has the factor table, reliabilities and known-group results; the You screen shows
4–6 constructs; and each construct has a documented unlock threshold.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S8), docs/METRICS.md, services/you.py,
> services/reference_axes.py, scripts/process_tal_chaos.py and the S6 population outputs. Plan the factor
> analysis, the reliability tests, the known-groups corpora (which games, how many, licensing), and the merge
> rules. Stop for approval, with no UI changes yet.*
>
> **Build prompt:** *Run the approved S8 analysis on `feat/s8-trait-science`. Results first (VALIDATION.md), then
> a separate PR for the construct changes and UI once I accept them.*

---

## S9 — Brilliant recalibration

**Goal:** a target band that is measured, not assumed (F6).

Tasks:

- Measure the Brilliant rate per rating band × time control on the population, under the current rules
  (rule v3 + S1 + S5).
- Re-measure Tal under the same pipeline on at least 200 games, with an interval.
- **ADR:** keep 6–10% as the aspirational "Tal-tier" band if the data supports it, or re-fit it. It's a
  CI-enforced contract (`test_philosophy_contracts.py`), so it changes only through the ADR.
- Add a personal **next band**: the player's interval plus one step.

**Done when:** the ADR is accepted and Home shows both the Tal-tier band and the personal next band.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S9), docs/adr/0001, 0004, 0007,
> tests/test_philosophy_contracts.py and scripts/process_tal_benchmark.py. Plan the measurement and the ADR
> options, and what the contract tests must assert afterwards. Stop for approval.*
>
> **Build prompt:** *Implement the approved S9 plan on `feat/s9-brilliant-band`. Measurements to VALIDATION.md,
> the ADR, the contract test updates (only as the ADR says), and the Home "next band".*

---

## S10 — New lenses: Originality and difficulty-adjusted performance

**Goal:** the analyses graders can't offer.

Tasks:

1. **Originality: the surprisal × EP-loss map.**
   - Surprisal = −log₂ P_human(move | the mover's converted rating).
   - Plot each move by surprise against EP loss. *High surprise with low loss* is the Tal quadrant; *high surprise
     with high loss* is reckless.
   - Trait: the share of moves in the Tal quadrant (shrunk and percentiled).
2. **Position difficulty**, from three signals:
   - human-policy entropy;
   - the gap between the best and second-best move;
   - Guid–Bratko depth instability (from the S2 node checkpoints).

   Calibrate it against population error rates, and against Lichess puzzle ratings as anchors. The puzzle
   database is Glicko-2 rated, about 6.2M puzzles.
3. **Difficulty-adjusted performance (IRT-lite):**
   - "You faced harder positions than 80% of your band, and handled them like a 1700";
   - one-parameter (Rasch) first, per theme later (sacrifice, defence, conversion);
   - compare with a Regan-style intrinsic rating as a neutral check. His group warned such models may favour
     positional players, so this is the bias check for Sarce's own metrics.
4. **Trap-ness:** the divergence between the human policy and the safe set (Jensen–Shannon), feeding the trap
   atlas and chaos map.

**Done when:** each lens has a validation entry (calibration and reliability), ships behind a flag until then, and
Review shows the surprisal × EP map for a game.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S10), lenses/base.py, lenses/registry.py, the S2 stored
> fields (entropy, top-k, node checkpoints) and services/trap_atlas.py. Plan the Originality lens, the difficulty
> model and its calibration data, and the IRT-lite fit, all as pure functions over stored data. Stop for
> approval.*
>
> **Build prompt:** *Implement the approved S10 plan on `feat/s10-originality` (lens and map) and
> `feat/s10-difficulty` (difficulty and IRT-lite) as two PRs. Flags off until VALIDATION.md has the results.*

---

## S11 — Clock hazard and session/tilt lens

**Goal:** the time and psychology lenses, measured within each player.

Tasks:

- **Clock hazard model:** the probability of a large EP loss as a function of remaining time, move-time ratio and
  position difficulty (S10), per player shrunk toward the band. Output: "your error risk doubles below N
  seconds; your band's doubles below M."
  - The 2026 PNAS study found faster decisions were associated with *better* quality in elite play, and long
    thinks signal difficulty. Copy says "long thinks tend to mean a hard position", never "think less".
- **Session and tilt:** within-player fixed effects with opponent-rating controls. A public 11M-game Lichess
  analysis found naive comparisons get the sign wrong. Output: "after two losses in a row, your next game runs
  about N points below your level".
  - This feeds the stop-loss nudge: a gentle "maybe take a break". It is never shown during a game, which also
    keeps it post-game only.
- Replace or absorb the current clock lens, as decided in S8.

**Done when:** both lenses are validated on held-out players, and the copy passes philosophy-check.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S11), lenses/clock.py, services/lens_service.py (clocks)
> and services/recap.py. Plan the hazard model, the fixed-effects tilt model, their validation by held-out
> player, and the copy. No causal wording. Stop for approval.*
>
> **Build prompt:** *Implement the approved S11 plan on `feat/s11-clock-tilt`. Stats in pure functions with
> tests, a validation run to VALIDATION.md, and UI behind a flag.*

---

## S12 — Compute at scale (parallel track)

**Goal:** keep the cost per game low enough for a free tier ([COMPUTE.md](./COMPUTE.md), ADR 0008).

Tasks:

1. **Measure** (benchmark Part C): CPU per game per stage, and the cache hit rate.
2. **Seed the cache** from the Lichess evaluation export (CC0, ~416M positions, updated monthly). Convert with
   the S5 EP model, with provenance `lichess-evaldb`.
3. **Tiered search:**
   - a cheap pass (low nodes plus Maia) on every ply;
   - deep MultiPV only where a lens can fire (sacrifices, large human-vs-engine divergence, eval swings, low
     clock, narrow safe sets);
   - acceptance: lens verdicts identical on ≥ 95% of moves.
4. **Recent-first queue:** the last 20 games on sign-up, a per-player fair share, then the backfill.
5. **Sarce Node beta**, if ADR 0008 is accepted:
   - a fishnet-style helper (outbound only, pinned engine builds, one thread, small hash for reproducibility);
   - it signs in as the player and writes only their games;
   - the server re-checks a random ~2% of results;
   - fishnet itself runs on about 64 MiB of RAM per core, which shows how light this can be.
6. **Browser engine** for the player's own fresh games, marked `local` in provenance.

**Done when:** the measured cost per game and per player is in COMPUTE.md, tiered search passes its acceptance
check, and the Node beta runs for at least three testers.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S12), docs/COMPUTE.md, docs/adr/0008,
> services/position_evals.py, services/job_queue.py and the benchmark Part C results. Plan the cache seeding,
> the tiered-search rules and their acceptance test, the queue fairness, and (separately) the Sarce Node protocol
> and packaging. Stop for approval.*
>
> **Build prompt:** *Implement the approved S12 plan as separate PRs: `feat/s12-cache-seed`,
> `feat/s12-tiered-search`, `feat/s12-queue-fairness`, then `feat/s12-sarce-node` only after ADR 0008 is
> accepted.*

---

## S13 — Grounded commentary

**Goal:** natural-language reads that never invent chess. Research on LLM chess commentary finds hallucinations
"pervasive" without tools, and less frequent when claims are grounded in tool output.

Tasks:

- Claude writes the summary paragraph **only** from a structured fact sheet: engine lines, human-model
  probabilities, lens verdicts, motif tags, the intent note.
- Every claim cites a fact ID. A checker rejects any sentence that isn't backed by a fact.
- Opt-in, with cost per read measured, and the cheap template copy kept as the fallback.

**Done when:** a sample of 100 reads has zero unbacked claims under the checker, plus a human spot check.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S13), services/summary.py, services/explain.py and
> services/ai.py. Plan the fact sheet schema, the prompt, the claim checker, and cost limits. Stop for
> approval.*
>
> **Build prompt:** *Implement the approved S13 plan on `feat/s13-grounded-reads`, behind a flag. Include the
> checker's tests and the 100-read evaluation.*

---

## S14 — Personal style models (12-month horizon)

**Goal:** a style measured in a learned space, not assembled by hand.

Background:

- Stylometry identifies a player among thousands with 98% accuracy from 100 games (NeurIPS 2021).
- Maia4All models an individual from about 20 games, instead of the 5,000 needed before.
- A centipawn-loss baseline identified players only 1.4% of the time. Engine-error statistics carry almost no
  style signal, which is why Sarce is built around human-model measures.

Tasks:

- **Style embedding per player**, from released models or a fine-tune. Measure it *net of rating*: model the
  deviation from rating-typical play, so that style ≠ strength.
- **Distance to an archetype:**
  - Tal, Shirov, Petrosian and Karpov embeddings from their games;
  - "this month you played 31% Tal-moves, up from 24%";
  - a "style twin", with uncertainty.
- **"What would you play here?"** and **"What would Tal-you play?"**, from personal models.
- **Style timeline:** change-point detection on the embedding and construct series ("your sacrifice rate
  stepped up in March").
- **Privacy:** embeddings stay private to the player. Never exposed or shared, because they can re-identify a
  person (rule 15).
- This needs a heavy dependency (PyTorch for training, or ONNX), so it needs an ADR and your approval.

**Done when:** archetype distances pass a known-groups test (Tal-model scores Tal games above Petrosian games on
held-out data), and the timeline is shown with read states.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S14), docs/adr/0002 and 0009, and the S8 results. Survey
> the released Maia4All and stylometry code and weights (licences, compute). Plan the embedding pipeline, the
> archetype set, the validation, and the privacy controls. Draft the dependency ADR. Stop for approval.*
>
> **Build prompt:** *Implement the approved S14 plan in stages: `feat/s14-embeddings` (offline pipeline +
> validation), then `feat/s14-archetypes` (API), then `feat/s14-timeline` (UI). Each one ships only after its
> validation passes.*

---

## S15 — Opening simulation and an open benchmark (12-month horizon)

**Goal:** numbers for preparation, and a contribution back to the field.

Tasks:

- **Monte Carlo vs Maia** at the opponent's (converted) rating, from the player's opening positions. Output:
  expected score per line ("against 1500s, 5…d5 scores 58% in simulation; the safe line 52%"). This feeds the
  chaos map and opponent prep, and shows its interval.
- **Repertoire predictability:** the entropy of the player's own choices, and how much opponents could exploit
  it.
- **Sarce Style Benchmark:** publish the population tables, the known-group results and the validation methods
  (CC0 data plus open code). The literature has no validated aggressive-vs-positional metric yet, so this is a
  real contribution, and a credibility asset for an open-source product.

**Done when:** the simulation is validated against real outcomes in the Lichess database (predicted line scores
vs observed), and the benchmark write-up is public.

> **Plan prompt:** *Read docs/STYLE_SCIENCE_PLAN.md (S15), services/chaos_map.py and services/scouting.py.
> Plan the simulation (games per line, depth, runtime), its validation against Lichess outcomes, and the
> benchmark package contents. Stop for approval.*
>
> **Build prompt:** *Implement the approved S15 plan on `feat/s15-simulation`, then `docs/s15-benchmark`. The
> simulation ships with intervals; the benchmark contains no player names.*

---

## Keep, merge, demote, add

| Decision | Items |
| --- | --- |
| **Keep** | Chaos (flagship; refit in S4), Brilliant (recalibrated in S9), intent journal (unique labelled data: intent is ground truth for future validation), trap atlas, chaos map |
| **Merge** (if S8 confirms) | Squeeze + Grip into Conversion; Swindle + Fight + Survival into Resourcefulness |
| **Demote** | Raw accuracy (context only); reference dots until S8 rebuilds them; the hand-built style label in `style_profile.py` |
| **Add** | Originality (S10), difficulty-adjusted performance (S10), clock hazard (S11), percentiles (S6), learned style (S14) |

## Open decisions (yours)

1. Maia-3 adoption (after S0): accept AGPL-3.0 as a separate process?
2. Only-move sacrifices: Brilliant or not (S1)?
3. Is it acceptable that the tier distribution changes when classification moves to EP (S5)?
4. Which constructs survive (S8): approve the merges.
5. The 6–10% band: keep or re-fit (S9)?
6. Heavy dependencies for S14 (PyTorch or ONNX) and Sarce Node packaging (S12).
7. Where the population data lives (object storage provider and region; see LEGAL.md on transfers).

## Rough timeline (part-time, solo)

| Month | Work |
| --- | --- |
| 1 | S0, S1, S2, S3; benchmark Part A; first hosted deploy |
| 2 | S4, S5; S12 measurement and cache seeding |
| 3 | S6, S7; tiered search |
| 4 | S8, S9; pilot (benchmark Part D) |
| 5–6 | S10, S11, S13; Sarce Node beta |
| 7–12 | S14, S15; publish the Sarce Style Benchmark |

## Sources (from the October 2026 research report)

- Maia-2 (NeurIPS 2024): <https://proceedings.neurips.cc/paper_files/paper/2024/hash/250190819ff1dda47cd23cecc0c5a69b-Abstract-Conference.html> · repository (Maia-3 recommended): <https://github.com/CSSLab/maia2>
- Maia4All, individual models from about 20 games: <https://arxiv.org/pdf/2507.21488>
- Behavioural stylometry (NeurIPS 2021): <https://mlanthology.org/neurips/2021/mcilroyyoung2021neurips-detecting/>
- Individual Maia models (KDD 2022): <https://www.cs.toronto.edu/~ashton/pubs/maia-individual-kdd2022.pdf>
- Regan, Intrinsic Chess Ratings: <https://cse.buffalo.edu/~regan/papers/pdf/RMH11.pdf> · 2024 talk: <https://cse.buffalo.edu/~regan/Talks/CogSciOct2024np.pdf>
- Guid & Bratko, Computer Analysis of World Chess Champions: <https://www.researchgate.net/publication/220174548_Computer_Analysis_of_World_Chess_Champions>
- Lichess accuracy and win% formulas: <https://lichess.org/page/accuracy>
- Chess.com move classification (expected points): <https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc>
- PNAS 2026, decision speed and quality: <https://www.pnas.org/doi/10.1073/pnas.2531472123>
- Tilt analysis, 11M Lichess games (not peer-reviewed): <https://github.com/romanbreyten/chess-tilt>
- Lichess open database, evaluation export and puzzles: <https://database.lichess.org/>
- IRT in chess (van der Maas & Wagenmakers 2005): <https://www.ejwagenmakers.com/2005/VanderMaasWagenmakersACTpaper.pdf>
- Rating comparison (ChessGoals): <https://chessgoals.com/rating-comparison/>
- fishnet protocol: <https://github.com/lichess-org/fishnet/blob/main/doc/protocol.md>
- LLM chess commentary evaluation (ACT-Eval 2026): <https://arxiv.org/pdf/2605.11893>
