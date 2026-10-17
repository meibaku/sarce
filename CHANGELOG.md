# Changelog

All notable changes to Sarce are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- v1.0 Review screen at `/games/{id}/review` (and the Review tab, which opens the latest game): moment chips,
  the design board with accent rings and corner ticks, idea arcs, the intent note before the engine's mirror
  line, "who falls for this", a two-move toggle and J / K / ← → / N / E shortcuts
- v1.0 Review API: `GET /games/{id}/review` (every moment with its board position, squares that mattered,
  question, P_fail at 800–2400, engine mirror line, plan outcome from the tagger and the saved note) and
  `PUT /games/{id}/moves/{ply}/intent`; migration `move_annotations` (RLS)
- v1.0 After-game Summary at `/games/{id}`: headline, outcome banner, this game's Brilliant % against the
  rolling window, up to three moments with the clock, and the one question "Did this game feel like you?"
  (`GET /games/{id}/summary`, `POST /games/{id}/felt`, migration `games.felt_like_you`). Style read is a
  provisional v0 score
- v1.0 Home on real data: `GET /users/home` (latest game style read, chaos strip and moments; Brilliant %
  over the last 64 games with its standard error; streak, sound : unsound and traps survived, hidden under
  5 games). The new Home replaces `/`; the old dashboard moves to `/lab`
- v1.0 UI foundation: light design tokens and IBM Plex, UI primitives (buttons, cards, move badges, Brilliant
  gauge, chaos strip, rook mark, icons), the app shell (desktop header, phone header and tab bar) and the Home
  view, previewed with the handoff sample data at `/preview/home`. The old dashboard keeps its dark theme via
  `.theme-lab` until its features move
- v1.0 design handoff intake: brand assets (7a rook mark, wordmark, app icon) in `apps/web/public/brand`,
  favicons, web manifest, and `docs/DESIGN.md` with the tokens, component rules and copy mapping
- Trap atlas data: `apps/api/data/trap_atlas.json` — 277 traps from 18,122 real one-minute games
  (openings pass, Maia-2); `build_trap_atlas.py` gains `--export`, `--load` and multiple `--samples`
- Chaos Lens M4 full-size validation: **GO** on 50,516 positions from twelve months of Lichess 1+0 games
  (held-out Brier 0.155 against 0.218 and 0.335 for the baselines); clock multipliers re-fit from it
- `validate_chaos.py` saves samples as it goes (`chaos_samples.partial.csv`), so a long run can be interrupted
- `HUMAN_MODEL=auto` is the new default: the validated Maia-2 model where its optional package is installed,
  the heuristic elsewhere
- Chaos Lens M4: four-month validation with widened safe sets (4,820 positions) — GO; clock multipliers for
  Maia-2 are now in `lenses/config.py` and applied to `P_fail` by the lenses
- Chaos Lens M8 (part): optional sign-in — the API verifies Supabase access tokens and scopes every
  request to the signed-in user; `AUTH_REQUIRED=true` makes it mandatory. Web: `/login` (email link)
  and a sign-in status in the header. Local-first behaviour is unchanged when nobody is signed in
- Chaos Lens M8 (part): durable per-user analysis job queue — `analysis_jobs` table with an atomic claim
  function, an in-process worker, `GET /games/jobs`. No new dependency; off by default
  (`JOB_QUEUE_ENABLED`), in which case BackgroundTasks is used as before
- Chaos Lens M4 pilot on real Lichess games (2,002 positions, Maia-2): GO — results in `docs/VALIDATION.md`.
  The sampler now caches repeated positions and takes `--max-ply`
- Chaos Lens M2: optional Maia-2 human model — `services/maia_model.py`, `HUMAN_MODEL=maia2`,
  `apps/api/requirements-maia.txt`. Off by default and not installed in CI
- ADR 0002: Maia spike findings — Maia-2 measured (MIT, 27.8 ms/position on CPU, full move distribution);
  Maia-3 is AGPL-3.0 and was not measured. Recommends Maia-2; integration awaits a decision
- Chaos Lens M8 (part): style focus picker (Brilliance / Chaos control) that changes dashboard emphasis only;
  Brilliant % stays the headline — see `docs/adr/0003-style-focus.md`
- Chaos Lens M8 (part): opponent scouting — private, aggregate-only preparation reports from a named
  player's finished games (`services/scouting.py`, `/scouting/*`, `scouting_reports`, Opponent prep panel),
  with deletion on request
- Chaos Lens M8 (part): Lichess import — `services/lichess.py`, `POST /games/import/lichess`, a site
  picker on the import form, and `games.source`. Finished standard games only
- `scripts/chaos_smoke.py` — runs the whole Chaos Lens pipeline on one PGN with a real engine and no database
- Chaos Lens M7 (UI): Ideas card in the game review — idea windows, what became of them, pivots, and
  motif chips for the selected move
- Chaos Lens M6 (trap atlas): `trap_atlas` table, `services/trap_atlas.py`, `scripts/build_trap_atlas.py`,
  `GET /traps`, and a Trap atlas panel with a drill mode. The atlas is empty until the validation
  sampler has been run on real games
- Chaos Lens M7 (intention tagger v1): engine-free motif detectors (`services/motifs.py`), idea windows
  with worked / refuted / fizzled verdicts and pivots (`services/ideas.py`), `move_tags` and `game_ideas`
  tables, `GET /games/{id}/ideas`. Off by default — set `IDEA_TAGGER_ENABLED=true` after migrating
- Chaos Lens M4 (tooling): `scripts/validate_chaos.py` and `services/chaos_validation.py` (stratified
  sampling, held-out split by game, calibration table, clock multiplier, baselines), plus
  `scripts/backfill_chaos.py` for games analysed before chaos data existed. The validation run itself
  is still to do — see `docs/VALIDATION.md`
- Chaos Lens M5 (review UI): chaos heat strip and key-move card in the game review (verdict badges,
  who-falls-for-it curve, clock), and a Chaos control panel on the dashboard
- Chaos Lens M3: `app/lenses/` (lens protocol, registry, soundness / chaos / survival lenses as pure
  functions), `move_lens_scores` table, `GET /games/{id}/lenses` and `GET /users/{u}/chaos-summary`
- Chaos Lens M2 (human model, part 1): `HumanModel` interface, `human_probs` cache table, the Elo ladder,
  and an interim engine-free heuristic model. The Maia-2 vs Maia-3 choice is still open — see
  `docs/adr/0002-human-model.md`
- Chaos Lens M1 (WDL + EP foundation): `services/ep.py`, node-limited MultiPV `StockfishEngine.analyse`,
  `position_evals` cache with adaptive MultiPV widening, per-ply clock parsing, and migration
  `20261010000000_position_evals.sql`. Off by default — set `POSITION_EVALS_ENABLED=true` after migrating
- Chaos Lens M0 housekeeping: `AGENTS.md`, `security-gates` CI job (secret scan + critical `npm audit`),
  `staging` ruleset config, promotion PR template, `pr:create` / `pr:promote` helpers
  (adapted from MeibakuHQ/ai-ci-repo-template)
- `docs/CHAOS_PLAN.md` — milestone plan for the chaos/survival style lenses (revised after review:
  complete safe sets, halfmove clock in cache keys, held-out validation set, `cook.py` is AGPL — reference only)
- `docs/PRODUCT_SPEC.md` — master product specification (Phases 1–4+)
- Phase 2 redefined: video position capture + transcript context
- Phase 3 redefined: move intent narratives + personal chess journal

### Changed
- CI and the philosophy check now run on pushes and PRs for `staging` as well as `main`
- `main` ruleset config targets `refs/heads/main` instead of the default branch
- `next` 15.5.19 → 15.5.27 and other in-range updates via `npm audit fix` (clears a critical advisory)

### Fixed
- Re-importing games no longer resets `analysis_status` to `pending` (it had left all 2,644 local games
  pending with only three analysed); new games still start as `pending` through the column default
- Chaos validation go / no-go compared a clock-adjusted model against an unadjusted heuristic baseline,
  so it could report GO when both were the same predictor; the baseline is now adjusted the same way
- Chaos review: the who-falls-for-it bars had no height; the dashboard chaos panel no longer disappears
  when an unrelated request fails; the uncalibrated "N in 10 players" sentence is removed (ADR 0002)
- Golden test fixture used an illegal move (`d1h5` with a pawn on e2), which crashed the engine instead of
  testing anything; replaced with a legal position
- Duplicate `listStyleMoments` export in `apps/web/src/lib/api.ts` that broke the web build

## [0.1.0] - 2026-06-13

### Added
- **Phase 1 MVP** — chess style analysis monorepo
- Next.js dashboard with Brilliant % gauge, distribution charts, timeline
- FastAPI backend: Chess.com import, Stockfish classification, Tal-style brilliant detection
- Supabase schema with RLS, style vectors, reference benchmarks
- Tal PGN benchmark batch job
- Local-first architecture (`docs/ARCHITECTURE.md`)
- Philosophy constitution (`docs/PHILOSOPHY.md`) and quality gates
- CI: api-test, web-lint, web-build, migration-check, philosophy-check
- GitHub ruleset "Protect main" with required PR + status checks
- Dependabot, CODEOWNERS, issue/PR templates
- pytest suite (unit, architecture, philosophy contracts, golden Stockfish)

[Unreleased]: https://github.com/meibaku/sarce/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/meibaku/sarce/releases/tag/v0.1.0
