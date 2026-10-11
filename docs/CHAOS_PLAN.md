# Sarce — Chaos Lens Gameplan (for Claude Code)

> Drop this file at `docs/CHAOS_PLAN.md`. Point Claude Code at it at the start of every session:
> *"Read docs/CHAOS_PLAN.md and docs/ARCHITECTURE.md. We're on Milestone N."*

## Status at a glance

| Milestone | Code | Still to do |
|---|---|---|
| M0 Housekeeping | Merged | Major-version Dependabot PRs, one at a time |
| M1 WDL + EP | Merged, off by default; verified on Stockfish 18 | Apply the migration to your own database |
| M2 Human model | Merged; default `auto` uses Maia-2 where installed, the heuristic elsewhere | Install `requirements-maia.txt` where you want calibrated numbers |
| M3 Lenses | Merged | Thresholds are provisional until M4 |
| M4 Validation | **GO** on the full 50,516-position run across twelve months (Maia-2); clock multipliers applied | Tune the verdict thresholds |
| M5 Review UI | Merged; checked against one analysed game | Check against your own games; Tal in chaos terms |
| M6 Trap atlas | Merged; 104 traps from 8,195 real games in `apps/api/data/trap_atlas.json` | Load it into your database (`build_trap_atlas --load`); most traps rest on 3–4 sightings |
| M7 Intention tagger | v1 merged, off by default | Tune thresholds; "sharpness" part of squeeze |
| M8 Sharing + scouting | Not started | Needs the multi-user decision first |

**What has actually been run** (10 Oct 2026, Stockfish 18, a throwaway Supabase Postgres + PostgREST stack):

- Node-limited `analyse`: identical lines on repeat, WDL present, about 4 s per position at 1.5M nodes.
- Phase 1 golden checks pass (after fixing a fixture that used an illegal move).
- All seven migrations apply in order; every public table has RLS enabled.
- One game analysed end to end through the real service code: 30 position evals, 180 probability rows,
  40 lens rows, 25 tags, 2 ideas; every new endpoint answered; a re-run reproduced identical evaluations.
- The review UI was opened against that data, which led to three fixes.
- `validate_chaos.py` and `build_trap_atlas.py` execute, on a synthetic PGN only.

**What that showed:** with the interim heuristic model the lenses over-trigger badly (an ordinary
`2. Nf3` was labelled real chaos; 8 of 17 moves counted as problems survived). The numbers are not
usable until a trained model is chosen and M4 passes on real data.

**Not run:** pytest on the development machine (blocked by device policy — CI runs it), anything against
the real local database (its container could not bind port 54322), and validation on real Lichess games.

### Turning it on

1. Apply the migrations in `supabase/migrations/` dated `20261010…` (five files, in order).
2. Set `STOCKFISH_PATH`, then run `npm run test:golden` — includes the determinism check for `analyse`.
3. Set `IDEA_TAGGER_ENABLED=true` (fast, no engine) and `POSITION_EVALS_ENABLED=true` (much slower per game).
4. Analyse new games as usual. For games already analysed: `python -m scripts.backfill_chaos`, and
   `GET /games/{id}/ideas?refresh=true` to tag one.
5. Decide the human model (ADR 0002), then run `python -m scripts.validate_chaos` and record the result
   in `docs/VALIDATION.md`. Until that passes, treat every chaos number as uncalibrated.

---

## Mission

**Recognizing better plays and having better chaos control.** Not elo-climbing.
Sarce scores how much *practical trouble* a move creates for a human opponent at a given
rating and clock — not just whether it was engine-perfect. Chaos is the **first style lens**;
the architecture must make later lenses (positional, survival, etc.) cheap to add.

## Ground rules for Claude Code

1. **Never break Phase 1.** Existing classification, Brilliant detection, baselines and the Tal
   benchmark must keep passing `npm run ci` and `npm run test:golden`.
2. **One milestone per branch / PR**, off `staging`. Small commits. Update `CHANGELOG.md`.
3. **Lenses are pure functions** over stored data. No lens may call Stockfish or Maia directly.
   Engines write raw data; lenses read it. Adding a lens must never require re-analysis.
4. **Expected points (EP), not centipawns,** for anything new. Centipawns stay only for Phase 1
   compatibility.
5. **Determinism:** engine searches use `go nodes N`, not depth or time, so results reproduce.
6. **Post-game only.** Never analyze a game that isn't finished. No live/in-game features, ever
   (Chess.com and Lichess fair-play rules).
7. **Schema changes = new Supabase migration** in `supabase/migrations/`. Never edit old ones.
   Every new table enables RLS with policies in the same migration — that is part of "done".
8. Ask before adding a new heavy dependency (torch, onnxruntime, celery, etc.).

---

## Target architecture

```
                 ┌──────────── raw data (engine layer) ─────────────┐
PGN + clocks ──► │ StockfishEngine: WDL, MultiPV-4, node-limited     │──► position_evals (FEN cache)
                 │ HumanModel (Maia): move probs at Elo 800..2400    │──► human_probs  (FEN+Elo cache)
                 └──────────────────────────────────────────────────┘
                                         │
                 ┌──────────── lenses (pure functions) ─────────────┐
                 │ soundness (Phase 1)  chaos  survival  brilliant   │──► move_lens_scores
                 └──────────────────────────────────────────────────┘
                                         │
                 ┌──────────── tagger (later) ───────────────────────┐
                 │ motifs per ply → idea windows → worked/refuted/pivot │──► move_tags, game_ideas
                 └──────────────────────────────────────────────────┘
                                         │
                                  Next.js review UI
```

### Core formulas

- **EP (expected points)** for side to move = `W + 0.5·D` from Stockfish `UCI_ShowWDL` (per-mille → 0–1).
- **Safe set** after the user's move: opponent replies whose EP is within `SAFE_TOL = 0.05` of the best reply.
  The stored lines must cover the whole safe set — a safe reply missing from storage is counted as a failure
  and inflates chaos.
- **P_fail(Elo)** = `1 − Σ P_maia(reply | Elo)` over replies in the safe set.
- **Stake** = opponent's EP(best reply) − weighted EP of their non-safe replies (how much they lose if they miss).
  Weighted over the non-safe replies that have a **stored** EP, with Maia probabilities renormalized over
  that subset; `details` records how much probability mass had no stored EP.
- **Chaos(Elo)** = `P_fail(Elo) × Stake`, set to 0 when the mover's EP before the move is > 0.9 or < 0.1 (game already decided).
- **Objective cost** = mover's EP loss vs. engine best move (from Phase 1 data, converted to EP).
- **Verdict:**
  - `real_chaos`: Chaos ≥ threshold **and** objective cost ≤ 0.05
  - `cheap_chaos`: Chaos ≥ threshold **and** objective cost > 0.10
  - `calculated_risk`: in between
- **Falls-for-it curve:** P_fail at Elo 800 / 1200 / 1600 / 2000 / 2400 per key move.
- **Survival (mirror lens):** when the *opponent* set a high-chaos problem, did the user find a safe reply?

All thresholds live in one config module and get tuned in Milestone 4 from data, not guesses.

---

## Milestones

Each milestone has: goal, tasks, files, acceptance criteria, and a prompt to paste into Claude Code.

### M0 — Housekeeping (½ day)

**Goal:** clean base before new work.

- Merge safe Dependabot PRs (patch/minor). Leave major bumps (Next 16, TS 6, ESLint 10, Recharts 3,
  setup-node/python v7) for a separate branch, one at a time, CI green each.
- Add this file as `docs/CHAOS_PLAN.md`; add a pointer to it in `docs/PHASES.md`.

**Done when:** CI green on `staging`, open PRs only contain deliberate major bumps.

> **Prompt:** *Read docs/CHAOS_PLAN.md. Do M0: list open Dependabot PRs by risk, propose which to merge now vs. later, and add docs/CHAOS_PLAN.md plus a link in docs/PHASES.md. Don't merge anything without showing me the list first.*

---

### M1 — WDL + EP foundation (2–3 days)

> **Status:** implemented on `feat/m1-wdl-ep`, gated by `POSITION_EVALS_ENABLED` (default off).
> Differences from the task list below: the cache key is `(fen_key, nodes)`; clocks live in
> `games.clocks_ms` (one array per game, every ply) rather than `game_moves.clock_ms`, because
> `game_moves` only has the user's moves; the decided-position skip uses stored Phase 1 evals
> converted to EP. Still to verify on a machine with Stockfish: `npm run test:golden`.

**Goal:** engine layer produces EP and MultiPV data, cached by position.

Tasks:
- `StockfishEngine`: enable `UCI_ShowWDL`; add `analyse(fen, nodes, multipv)` returning
  per-line `{move_uci, cp|mate, wdl, ep}`. Use `go nodes` (config `ANALYSIS_NODES`, default 1_500_000).
- New `services/ep.py`: `wdl_to_ep()`, `cp_to_ep()` fallback, mate handling.
- New migration: `position_evals` (fen_key PK = FEN without the fullmove number — keep the halfmove clock,
  it changes fifty-move-rule evals — nodes,
  multipv, lines jsonb, engine_version, created_at). Cache lookup before every search.
- Clock parsing: extract `%clk` for **every ply, both players** (new nullable storage). `%clk` is the
  mover's time *after* their move, so the clock that matters for a lens position is the
  decision-maker's previous annotation (or the initial time control) — store or derive that explicitly.
- For each **user move**, run MultiPV-4 on the resulting position (opponent to move) and store it.
  If the 4th line is still within `SAFE_TOL` of the best, widen MultiPV until the first line outside it
  (cap in config), so the safe set is complete.
- Do the same for each **opponent move** (user to move): the survival lens needs those positions,
  and lenses may not call the engine later.
- Skip plies where the mover's EP before the move is > 0.95 or < 0.05.

Files: `app/services/stockfish.py` and `app/services/analysis.py` (existing — extend, don't duplicate),
`app/services/ep.py`,
`supabase/migrations/<ts>_position_evals.sql`, `tests/test_ep.py`, `tests/test_position_cache.py`.

**Done when:**
- Unit tests: WDL→EP, mate→EP, cache hit avoids engine call, clock parsing on a sample PGN.
- Re-analyzing the same game twice gives identical stored lines (determinism).
- Phase 1 golden tests still pass.

> **Prompt:** *Read docs/CHAOS_PLAN.md and docs/ARCHITECTURE.md. Implement M1 on a new branch `feat/m1-wdl-ep`. Start by reading the current StockfishEngine, MoveClassifier and AnalysisService and summarize how they work before changing anything. Keep Phase 1 behavior identical. Write tests first for ep.py and clock parsing.*

---

### M2 — Human model (Maia) (3–4 days)

> **Status:** interface, cache table, Elo ladder and an interim heuristic model are implemented.
> **Not done:** the Maia spike and the model choice — they need a heavy dependency (rule 8) and a
> decision; see `docs/adr/0002-human-model.md`. Until then chaos numbers are *not* calibrated.

**Goal:** P(move | Elo) for any position, cached.

Tasks:
- **Spike first (half a day):** benchmark Maia-3 5M via its UCI engine vs. Maia-2 (`pip install maia2`)
  on CPU. Measure ms/position and install pain on Windows. Check Maia-3's licence. Pick one; write the
  decision as an ADR in `docs/adr/`.
- New `services/human_model.py` with interface `move_probs(fen, elo) -> dict[uci, float]`, behind an
  abstract base class so the model can be swapped.
- Migration: `human_probs` (fen_key, elo, model_version, probs jsonb, PK on fen_key+elo+model_version).
- Run at `ELO_LADDER = [800, 1200, 1600, 2000, 2400]` + the opponent's actual rating (rounded to 100).
- Bullet note: models are blitz-trained. Store the raw output; clock adjustment comes in M4.

**Done when:** a sample position returns a probability for **every legal move**, summing to ~1 at each Elo
(a distribution over engine candidates only does not count), cached on second call,
and the ADR exists.

> **Prompt:** *Read docs/CHAOS_PLAN.md. Do the M2 spike only: set up Maia-3 (5M, CPU) and Maia-2 side by side in a scratch script under apps/api/scripts/, time 200 positions each, report install steps, speed and licence. Don't integrate yet — write the findings to docs/adr/0002-human-model.md and stop for my decision.*

---

### M3 — Chaos + survival lenses (3–4 days)

> **Status:** implemented. Lens results attach to the user's moves: chaos scores the position the
> user left, survival scores the position the user faced. Thresholds in `app/lenses/config.py` are
> provisional until M4, and scores use the interim heuristic human model until ADR 0002 is decided.

**Goal:** the first real style lens, pure and testable.

Tasks:
- New package `app/lenses/` with `base.py` (`Lens` protocol: `name`, `version`, `score(ply_ctx) -> LensResult`),
  `soundness.py` (wraps Phase 1 result), `chaos.py`, `survival.py`, and a registry.
- `ply_ctx` is built from stored data only (`position_evals`, `human_probs`, clocks, Phase 1 classification).
- Migration: `move_lens_scores` (game_move_id, lens, lens_version, score numeric, verdict text,
  details jsonb incl. P_fail per Elo, stake, safe set, objective cost).
- `app/lenses/config.py`: `SAFE_TOL`, chaos threshold, decided-position cutoffs. (Not an `app/config/`
  package — that would shadow the existing `app/config.py`.)
- API: `GET /games/{id}/lenses` returns per-move lens results; `GET /users/{u}/chaos-summary` returns
  counts of real/cheap/calculated chaos and survival rate.

**Done when:**
- Hand-built test fixtures cover: obvious recapture (low chaos despite big cliff), hidden only-move
  defence (high chaos), already-won position (zero), cheap chaos (high chaos, losing move).
- Adding a dummy lens to the registry requires no engine re-run (test proves it).

> **Prompt:** *Read docs/CHAOS_PLAN.md. Implement M3 on `feat/m3-chaos-lens`. Build app/lenses with the Lens protocol and registry first, then chaos and survival as pure functions using only stored data. Write the four fixture tests listed under M3 before implementing chaos.py.*

---

### M4 — Validation on real bullet data (3–5 days, mostly compute)

> **Status:** the script and its maths are implemented and unit-tested; **the run has not happened**.
> It needs a local Stockfish, a Lichess database file and a trained human model (ADR 0002).
> The go / no-go checkpoint is therefore still open — see `docs/VALIDATION.md`.

**Goal:** prove the score means something; tune thresholds from data.

Tasks:
- `scripts/validate_chaos.py`: stream one month of the Lichess open database (CC0), keep 1+0 games
  with clocks, sample ~50k positions stratified by rating band (200-pt) and opponent clock
  (<5s, 5–15s, 15s+).
- For each sampled user move: compute chaos, then label whether the opponent's *actual* reply left the
  safe set (lost more than `SAFE_TOL` EP) — the same event `P_fail` predicts. A ≥ 0.10 EP loss can be
  reported as a second, separate label.
- Output: calibration table + chart (predicted P_fail vs. observed error rate, per band and clock bucket),
  compared against two baselines: raw cliff only, and heuristic findability (capture/check/forward).
- Fit a simple clock multiplier per clock bucket. Write it to `app/lenses/config.py`.
- Split the sample by game into a tuning set and a held-out test set. Fit thresholds and the clock
  multiplier on the tuning set only.
- Write results to `docs/VALIDATION.md`.

**Done when:** the chart exists and chaos beats both baselines **on the held-out set**. If it doesn't, stop and rethink before M5.

> **Prompt:** *Read docs/CHAOS_PLAN.md. Build scripts/validate_chaos.py for M4. Start with 2,000 positions to check the pipeline end to end and report runtime, then I'll decide the full sample size. Save outputs under apps/api/scripts/out/ (gitignored).*

---

### M5 — Review UI (4–5 days)

> **Status:** first version implemented inside the existing Style lab and dashboard. Not done: the Tal
> reference in chaos terms (needs the Tal corpus run through the raw-data pass), and the
> "review your last 20 bullet games" acceptance check, which needs real data.

**Goal:** make it feel like a coach, not a spreadsheet.

Tasks in `apps/web`:
- Game review page: board + move list, **chaos heat strip** under the eval graph, badges per move
  (Real chaos / Cheap chaos / Calculated risk / Survived / Missed).
- Key-move card: before/after board, "who falls for this" curve (P_fail by Elo), and one plain sentence
  ("At 1200 bullet, ~6 in 10 players miss the only defence here.").
- Dashboard: real vs. cheap chaos over time, survival rate, Tal reference re-expressed in chaos terms.
- Clock shown next to every flagged move; errors under 5s labelled "clock error."

**Done when:** you can review your last 20 bullet games and the flagged moves match your memory of them.

> **Prompt:** *Read docs/CHAOS_PLAN.md. Implement the M5 review page using the existing web app's components and styling. First show me a component plan and the API calls it needs, then build it.*

---

### M6 — Rating-band trap atlas (3–4 days)

> **Status:** table, builder, endpoint and UI (browse + drill) are implemented. **The atlas is empty**
> until `scripts/validate_chaos.py` has been run on real games and `scripts/build_trap_atlas.py` has
> loaded the result. Browsing by the user's own openings is not done — only a rating-band filter.

**Goal:** "ideas that work at your level."

- From the M4 pipeline, collect positions where the most-played reply at a band loses ≥ 0.2 EP.
- Table `trap_atlas` (fen_key, band, speed, frequency, p_fail, stake, opening ECO).
- UI: browse traps for your band and your openings; drill mode (play the move, see the common blunder).

---

### M7 — Intention tagger v1 (1–2 weeks)

> **Status:** v1 implemented, engine-free. Motif detectors were written from scratch (no `cook.py`
> code). Squeeze uses the opponent's mobility and the user's EP only — the "sharpness falling" part
> needs stored engine lines and is not included. Thresholds in `services/ideas.py` are untuned.

**Goal:** "Did I have an idea, did it land, did I pivot?"

- Re-implement motif detectors, using Lichess's `lichess-puzzler` `cook.py` only as a reference for *which*
  motifs matter — it is **AGPL-3.0**, so do not copy or port its code into this MIT repo: pin, fork, skewer, sacrifice,
  discovered attack, hanging piece.
- Idea windows (rules, configurable): **Gambit** (≥1 pawn down for ≥6 plies with EP ≥ 0.4),
  **King attack** (≥3 own units enter enemy king zone within 8 plies), **Squeeze** (opponent mobility and
  sharpness falling while EP rises).
- Verdicts: worked / refuted / fizzled; **pivot** = dominant idea family changes within N plies after a refutation.
- Tables `move_tags`, `game_ideas`. This becomes the foundation every future style lens reuses.

---

### M8 — Sharing + opponent scouting (later)

> **Status:** Lichess import, opponent scouting and a style focus picker (ADR 0003) are implemented. A durable per-user analysis
> job queue (`JOB_QUEUE_ENABLED`) and optional sign-in (`AUTH_REQUIRED`) are implemented too; sign-in is untested against a live Supabase Auth.

- Multi-user: auth flows, per-user queues, replace `BackgroundTasks` with a real job queue.
- Style picker: users choose their lens; dashboard mirrors that identity.
- Opponent scouting: **finished games only, private reports, only usernames the user types in,** deletion
  on request. No public directory of anyone's weaknesses.
- Lichess import.

---

## Rough timeline (part-time, solo)

| Weeks | Milestones |
|---|---|
| 1 | M0, M1 |
| 2–3 | M2, M3 |
| 4 | M4 (validation) — **go / no-go checkpoint** |
| 5–6 | M5 (UI) — first version you actually use |
| 7–8 | M6 (trap atlas) |
| 9–12 | M7 (intention tagger) |
| later | M8 |

## Session habits with Claude Code

- Start each session: *"Read docs/CHAOS_PLAN.md, we're on M_. Summarize what's done and what's next."*
- Ask for a plan before code on anything touching the analysis pipeline.
- End each session: have it tick off tasks in this file and add a line to `CHANGELOG.md`.
- If a session drifts into live/in-game features, stop — rule 6.

## Open decisions (yours)

1. Maia-3 vs. Maia-2 (decided in M2 spike; check Maia-3 licence for commercial use).
2. Chaos threshold and SAFE_TOL (decided by M4 data).
3. When to go multi-user: right after M5, or after a second lens exists.

---

## Feasibility report reference

This plan is grounded in a feasibility & strategy report ("Sarce Feasibility & Strategy Report:
Chaos Lenses, Human-Move Models, and a Solo-Dev Build Plan"). Its verdict: **feasible for a solo
developer**, provided three deviations from naive "chaos scoring" are followed —

1. **Findability driven by a rating-conditioned human-move model** (Maia-2/Maia-3), not hand-made
   heuristics.
2. **The "cliff" measured in expected points / WDL**, not centipawns (Stockfish's centipawn scale is
   calibrated to a 50% self-play win rate at fast time controls and is not comparable across games
   or linear near decided positions).
3. **The intention layer starts as a small motif-and-phase tagger**, not open-ended plan recognition.

Every core building block (MultiPV Stockfish, WDL→EP conversion, the CC0 Lichess database with
per-move clocks, Lichess's open-source tactics tagger `cook.py` — AGPL, reference only) already exists and is free; the
hard parts are calibration, validation, and compute budgeting — not invention. This matches the
precedent of the 2006 "Trappy Minimax" idea (trappiness × profitability), which raised Beowulf's
rating against humans on ICC from 2262 to 2440.

Key implications baked into the milestones above:
- Neither Chess.com's Classification V2 nor Lichess's server analysis scores *practical trouble*
  for the opponent — both grade the mover's own EP loss. That gap is Sarce's opening (see Mission).
- No public human-move model handles bullet clocks out of the box (Maia-3 is blitz-trained and
  never sees clock format); M2/M4 approximate via a lowered effective Elo or a clock multiplier
  fit from Lichess bullet data, rather than assuming one exists off the shelf.
- Fair-play rules from both platforms draw a clean line at "during the game" — post-game analysis
  is unambiguously fine, which is why rule 6 (post-game only, no live features) is non-negotiable.
