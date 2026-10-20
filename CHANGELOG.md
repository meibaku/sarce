# Changelog

All notable changes to Sarce are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Removed
- The pre-v1 dashboard at `/lab` and the components only it used (ADR 0005); the Brilliant headline contract now
  checks Home; sign-in status moved to Settings

### Fixed
- Reference players: pgnmentor spells Tal "Mihail", so name matching failed and every Tal game counted him as
  White; matching now accepts surname plus first initial. The Tal axis values from the earlier run mixed in his
  opponents and were removed until the rerun
- Background analysis no longer freezes the API: move classification runs in a worker thread

### Added
- Dark theme (the v1.1 item Settings promised): Settings → Theme → Light / Dark / Match system; dark tokens keep
  every text colour at 4.5:1 or better, the fingerprint ramp follows, and the choice is applied before first
  paint (no flash)
- Manual position setter (PHASES 2.1): Train → "Save a position from a video or book" takes a FEN with a live
  board preview and saves it as a drill
- The Expo app (`apps/mobile`, SDK 58, own lockfile): Home, Review, You, Train and Play tabs plus Summary with its
  questions, Review with intent notes and "Add to Train", the library, the weekly recap, Settings with sync,
  onboarding and games against Sarce bots, on the same API (`EXPO_PUBLIC_API_URL`); the handoff's app icons and
  splash; the rook mascot (the handoff's motion maths drawn with react-native-svg, still under Reduce Motion);
  CI job `mobile-check` (typecheck + lint); the API allows the Expo web dev origin
- Opponent prep at `/prep` (from Play): private reports from an opponent's finished games, in the v1 design
- Openings (ECO extraction, PHASES 1.8): `games.eco` and `games.opening` from the PGN headers (migration
  `game_openings` backfills stored games); Train adds "Tal in your openings" (guess Tal's move in a position
  from a Tal game in an opening you play, `data/reference_positions.json` from
  `scripts/build_reference_positions.py`) and puts traps from your openings first; the library filters by opening
- Saved positions: Review → "Add to Train" keeps the moment's position (migration `saved_positions`, with the
  engine's move as the answer when the game was analysed) and Train drills it as "a saved position"; the
  library's "Defend it yourself" opens that sacrifice's defence drill (`/train?drill=`); Settings → "Export
  journal (PDF)" opens a print-styled journal (`/journal`) for the browser's Save as PDF
- Faster analysis: several games are analysed at once, one single-threaded Stockfish each (`ANALYSIS_WORKERS`,
  default one per core minus one; results stay deterministic); with the chaos pass on, Phase 1 reads the same
  per-position search as the lenses instead of three depth-18 searches per move; a Stockfish folder with
  several builds uses the fastest one the CPU can run
- Tal on the You axes in chaos terms: `scripts/process_tal_chaos.py` runs a local copy of the Tal corpus through
  the same classification and Chaos Lens as your games, in memory, and writes the four axis values to
  `data/reference_axes.json`; You draws a T dot per axis once that file exists, and says Tal isn't scored yet
  until then
- Train move input: drills are played on the board (click a piece, then a highlighted square) and checked on the
  server (`POST /users/train/check`): the answer, another move that still holds, or one that lets the problem
  through; "find the sacrifice" drills want the sacrifice itself
- Bot games are saved for review: a finished game against a Sarce bot (`POST /play/save`, migration
  `sarce_bot_games`) is stored with its clocks, analysed in the background and opens in Summary and Review;
  bot games stay out of Brilliant %, the fingerprint, the recap and the library
- Distraction check-ins: a detector reads move times from the PGN clocks and flags a costly move played far
  faster than your own pace, a fast reply to a real problem, or a long pause in a quiet position (skipping the
  opening, premoves, time trouble and daily games); the strongest flag becomes a ?! "Your pace changed here"
  moment on Home, Summary and Review and the target of the Summary check-in
- Automatic game sync: with `AUTO_SYNC_ENABLED` on, the API fetches new finished games every `SYNC_MINUTES` for
  the Chess.com / Lichess usernames saved in Settings (or at onboarding) and analyses up to five pending games,
  newest first; `GET/POST /users/sync` report and start a sync, the header shows the account line and Settings
  gains the username fields and "Sync now"
- After-game question rotation and intention grading: Summary asks up to the question budget, rotating between
  "Did this game feel like you?", the intent prompt on a moment and a random check-in ("Was something going on
  here?", migration `game_answers`), and grades the game against today's intention first
- v1.0 motion, finished: the launch intro (trace then hello, once per session; a still for reduced motion), the
  header mark tipping on navigation, and mascot toasts for a saved note, a set intention, the felt-like-you
  answer, a changed goal and the quiet week
- v1.0 mascot and motion: the handoff's rook mark and skits (dependency-free web components in
  `apps/web/src/lib/motion`) on Home, the Summary banner, Review, Train, Recap, Onboarding, Settings and every
  edge state; Settings → Playful mascot and Motion (follows `prefers-reduced-motion` by default) decide how
  much plays, and a quiet week turns skits off
- v1.0 edge states and Onboarding: one shared `EdgeState` (no games, still analysing, analysis failed, too few
  games, tracking paused, offline; 56px line icon, title, sentence, one action) now used on every screen;
  `/states` previews them; `/onboarding` connects a username (imports and starts analysis), shows a real
  moment from the last game, sets the style goal and explains the one-question rule
- v1.0 Settings at `/settings` (`GET`/`PUT /users/settings`, `GET /users/journal`): style goal steppers with a
  live gauge, question budget, quiet week, sources, theme, model card, what Sarce keeps, journal export
  (Markdown) and mascot / motion preferences (migration `profiles.settings`). Home shows the quiet-week
  variant and Summary drops its question when the budget is None
- v1.0 Play at `/play` and 3+0 games against Sarce bots at `/play/game` (`/play/bots`, `/play/start`,
  `/play/move`): Defender · 1600 (human-like among sound moves), Tal-style attacker (the sound move with the
  highest P_fail × stake for you) and Swindler (wider margin). Stateless, one shared engine, clicks to move;
  today's intention is saved for the next summary
- v1.0 Train at `/train` (`GET /users/train`, `POST /users/train/answer`): one queue from your games (the
  sacrifice you didn't play, defend your own sound sacrifice) and the trap atlas at your band, ordered by the
  week's focus, with "How sure were you?" spacing (tomorrow / 3 days / 9 days; migration `drill_reviews`)
- v1.0 Weekly recap at `/recap` (`GET /users/recap`): the week's games as bars, Brilliant with the change from
  the week before, best moment, how last week's focus went, and picking next week's focus. `GET`/`PUT
  /users/focus` stores the weekly focus and today's intention (migration `user_focus`, RLS)
- v1.0 Sacrifice library at `/library` (`GET /users/sacrifices`): every genuine offer newest first, with what
  was given, Held / Didn't hold, your note, a link into Review and a share-card PNG. A stricter "real offer"
  rule (piece left to a cheaper attacker, or undefended) now feeds the library and the Home, Summary and You
  sacrifice counts; Phase 1's broader `sacrifice` signal is unchanged
- v1.0 You screen at `/you`: Brilliant with its 12-week trend and tap-for-formula, the style fingerprint,
  your reference axes (reference players shown as not yet scored, no ranking), the time-control split with
  uncalibrated badges, the survival story and the door to the sacrifice library
- v1.0 You API: `GET /users/you` (Brilliant % with its 12-week trend and formula counts, the style
  fingerprint of 5 traits × 12 weeks with a one-line reading, your values on the reference axes, the
  bullet / blitz / rapid split, the hardest problem faced and the sacrifice counts)
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
- Brilliant also means hard to find (ADR 0004): after the human-model pass, a Brilliant move that players at
  the opponent's rating find more than 20% of the time becomes "best"; the game's vector becomes version 2
  (`brilliantRule: find-rate-20`). `scripts/backfill_brilliant_find_rate.py` applies it to analysed games;
  the You trend marks the week the definition changed
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
