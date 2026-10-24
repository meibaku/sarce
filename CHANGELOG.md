# Changelog

All notable changes to Sarce are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed
- Tal benchmark (review F6): `process_tal_benchmark` now runs the same pipeline as a player's games (the shared
  engine search, classification, then the find-rate and real-offer post-pass), on an evenly spaced sample across
  the career, skipping games Tal isn't in. It used to classify the first N games with no find-rate rule and fell
  back to a guessed colour

### Added
- One focus a week (plan 3.2): Home names one trait, the one whose last 80 games sit lowest among twelve 40-game
  stretches of your own history, with a target from your own range ("Sacrifice: last 80 games 1.0%; aim for 2.0%").
  Pick one yourself in the Recap (the nine traits join the weekly focuses); the Recap says whether this week's games
  moved it, and only "up" or "down" when the ranges separate. Brilliant is never the focus. Web and Expo
- Brilliant disagreements, part 2 (plan 3.3): "Chess.com called this Brilliant" in Why this move? (web, Expo) stores
  a report with the clause Sarce's rule stopped at (new `brilliant_reports` table, RLS, no free text) and tells you
  which condition made the difference; `scripts/brilliant_reports.py` counts them by clause for Benchmark B.
  From the review of part 1: the find-rate copy says "more often than the 20% cutoff", the definition counts the
  sacrifice after what the move captures, Expo shows almost-Brilliant moves on games with no moments and links
  `!!` to the definition
- Brilliant disagreements, part 1 (plan 3.3): a real sacrifice that misses exactly one Brilliant clause is marked
  "almost Brilliant" (`near_brilliant:<clause>` signal, set by the rule pass) and Review names the clause ("it gave a
  little more than the best move"), web and Expo. Every `!!` links to a public page, `/brilliant`, that lists the six
  clauses with the thresholds read from the API (`GET /public/brilliant/definition`), so it can't drift from the rule.
  `backfill_brilliant_find_rate --all` re-judges games already on the current version
- On top of the sites (plan 3.4a): Review links the move on the board to the same move on Chess.com (`?move=N`) or
  Lichess (`#N`), web and Expo. Home opens with a line for the games analysed since your last visit ("6 games
  analysed, 2 that felt like you, 1 real problem set"), counted by when analysis finished (`games.analysed_at`,
  new); `/users/home?since=` returns `session`
- Chaos budget (plan 3.9): Summary shows what setting problems cost in a game and what your opponent's replies gave
  back ("chaos budget · 0.27 risked · 0.40 came back", expected points), and You shows the last 20 games. The chaos
  lens now stores the opponent's actual reply and its EP loss (version 3); re-score with `scripts/rescore_lenses.py`
- Fingerprints by time control (plan 3.8): You's "By time control" card shows the nine traits for the chosen class,
  each with its 95% range, and one sentence naming where your two main classes differ beyond noise ("In rapid you
  set problems more often; in bullet you keep a winning position tight more often"). Each class reads up to 100 of
  its own newest games, reaching past the 500-game window when recent games are all one speed. Web and Expo
- `docs/PHASE3_PLAN.md`: Phase 3 (product) in waves: items needing no engine first (3.1, 3.8, 3.9, 3.4a, 3.3), then
  weekly focus and quests and opponent-aware chaos, with style cards and the style twin waiting on Phase 2 and the
  owner-gated items listed with suggested defaults
- A personal next band (plan 1.3): Home and Settings show a dashed step on the Brilliant gauge, from just above your
  likely range (its 95% upper bound) to half as much again, on the way to the goal band, with one line naming it.
  Web and Expo; `/users/home` returns `nextLo`/`nextHi`. Hidden within half a point of the goal
- `scripts/trait_overlap.py` and `docs/TRAIT_OVERLAP.md` (review F10a): the nine traits' correlation over 81 windows of
  20 games. No pair moves together (|r| > 0.8; the strongest is Initiative–Grip at −0.77), so all nine stay; Calm's
  narrow range is already handled by the per-trait fingerprint scale
- `brilliant_clauses()`: each Brilliant clause on its own (real sacrifice, sound, not already winning, not
  forced, hard to find); `is_brilliant_move` is now built on it
- `services/brilliant_benchmark.py` and `scripts/benchmark_brilliant_v3.py`: Brilliant % under rule v3 with a
  game-level bootstrap interval, and the first clause stopping each real sacrifice, for a reference player (engine)
  and for you (stored data, seconds). Locally (1,626 games): your Brilliant is 0.02% (0.01–0.04%). Of 489 real
  sacrifices, 440 failed "sound" and 31 came when already winning; 11 reached the find-rate clause

### Added
- `docs/IMPLEMENTATION_PLAN.md`: every suggestion from the October review and its companion docs as ordered work
  items (phases 1–5), with size, dependencies, ADR/engine/data needs and the decisions only the owner can make.
  F2, F4 and F12 are marked done; F6 moves to the front after F4 showed Brilliant at 0.01% under rule v3

### Changed
- Time to first read (plan 3.1): importing an account stores and queues the newest 20 games before answering, then
  fetches older Chess.com months (newest first) or the remaining Lichess games in the background and queues them.
  Before, every archive was fetched first. The first import and first completed analysis are recorded on the
  profile (sync or import), and `GET /users/sync` returns `firstReadSeconds`
- `docs/IMPLEMENTATION_PLAN.md`: Phase 1 progress (1.1, 1.3 part, 1.4–1.10, 4.7 done; Tal under rule v4 and the band
  decision open); a squeeze test where the stored WDL-based EP decides the verdict, not the centipawn score
- Lenses in one unit (review F8): squeeze, swindle, clock and prophylaxis judge edges and costs in expected points
  like chaos, not centipawns. Thresholds equal the old ones in a level position, so a pawn given back at +8 no
  longer counts as "gave air" and a won position where every move still wins is no longer "critical". Squeeze's
  room count stays in centipawns (documented: EP compresses on the losing side). Lens versions → 2; re-score with
  `scripts/rescore_lenses.py` (stored data, no engine)
- Brilliant rule v4 (ADR 0009, review F5): sound = at most 0.03 expected points below the best move (one-sided);
  no Brilliant when already lost (under 0.10 EP); "not forced" = another move kept you within 0.10 EP of the best,
  not just "more than one legal move". The post-pass re-judges every stored move from scratch, so rule changes
  promote as well as demote; style vectors → version 5. "Why this move?" builds its checklist from the same
  clauses. Locally: 3 Brilliant moves in 30,756 (0.01%) against 6 under v3
- Ratings on the human model's scale (review F1): Maia-2 is conditioned on Lichess ratings, so every Chess.com
  rating is converted first (`services/rating_map.py`, from the public ChessGoals survey, July 2026) wherever it
  meets the model: lens ladder, chaos map, Review's "who falls for this", Why this move. A Chess.com rapid 660
  opponent is now judged as the ~1,170 player they are, not the bottom rung. Chaos and survival lens versions bump
- The Brilliant find-rate clause is judged at your own rating, converted and to the nearest 100, instead of the
  opponent's at 400-point rungs (review F11a, ADR 0004 addendum); `games.user_rating` is a new generated column
  from the PGN. Style vectors → version 4
- Traps (review F7, the winner's curse): Your traps and the trap atlas rank by a cautious estimate, the 95% lower
  bound of how often a trap catches opponents, so a lucky 3 of 3 can't outrank 30 of 40. Your traps show "likely at
  least N%" next to the raw rate; the atlas returns `seen` with each trap
- Honest uncertainty (review F4), in a new `services/uncertainty.py`:
  - Brilliant % shows its Wilson 95% range ("likely 3.2–5.0%") on Home, You and Recap, web and phone.
  - The You trend is Brilliant % over rolling 20-game windows, drawn as a line in its shaded range, instead of one
    noisy point per week.
  - Recap says "up" or "down" only when this week's and last week's ranges separate; otherwise "about the same as
    last week".
  - Every trait reports the events it rests on, and is dashed below 30, overall and per week.
- You: the fingerprint labels now take one row per trait. They were fixed at five rows, so with nine traits the
  later labels drifted out of line with their week cells

### Changed
- Sacrifice trait (review F2): it now counts only real sacrifices, a minor piece or more genuinely on offer (the
  test Brilliant uses since ADR 0007), through a new `real_sacrifice` move signal. The loose signal counted any
  piece a reply could land on: locally only 349 of 3,807 tagged moves really offered a piece. The You axis is now
  "Sacrifices per 1,000 moves" (as a percentage everyone rounds to 0–2), and the references are rescored
  board-only: Tal 5, Shirov 7, Morphy 16. Tal still isn't first; with 7 events in 40 games that awaits F3/F4's
  larger samples and intervals. `scripts/backfill_real_sacrifice.py` and `scripts/rescore_reference_sacrifice.py`
  need no engine. The stored style vector's `sacrificeRate` is unchanged and unread, so no version bump

### Docs
- Planning and review docs:
  - `docs/REVIEW_2026-10.md`: trajectory, statistical findings F1–F11, Brilliant disagreement plan, feature ideas;
  - `docs/BENCHMARK.md`: Lichess and Chess.com comparison, cost measurement, style pilot;
  - `docs/COMPUTE.md` and ADR 0008 (proposed): shared cache, Sarce Node, browser engine, cloud;
  - `docs/LEGAL.md`: licensing, CLA, trademark, third-party terms, privacy (Tanzania PDPA, GDPR, minors);
  - `docs/SUSTAINABILITY.md`: free / Plus / Coach tiers.
- README phase table: Phases 2 and 3 marked complete

### Fixed
- Game results: the Chess.com import read White's own outcome code backwards ("resigned", "timeout" and
  "abandoned" counted as White wins; every draw code as a White loss), so about a third of stored results were
  inverted. This affected Summary's won/lost variants, Recap, comebacks, wins on time and scouting reports. The
  parser now uses the PGN's [Result] header, with the Chess.com codes read correctly as a fallback. Migration
  20261023000000 repairs stored games (1,167 of 3,200 locally)
- Analysis: an engine timeout or crash under heavy CPU load sends the game back to the queue (up to 3 tries),
  instead of marking it failed for good

### Fixed
- Chess.com game downloads now send Sarce's contact User-Agent, like the archive-list request already did
  (Chess.com's PubAPI guidance)

### Added
- The prophylaxis lens: stopping the opponent's idea before it happens. The analysis pass now stores each faced
  position's threat (a short null-move search: the opponent's best move if you passed, in a new table
  `position_threats`). Real threats (worth 1.5+ pawns to them) are stopped by a quiet move, met by force, or let
  through. Adds a **Foresight** trait, a "Stopping their ideas" card on You and a "Their ideas" list in Review.
  `scripts/backfill_threats.py` stores threats for games analysed before (needs Stockfish)

### Added
- Your traps (You, web and phone): the opening positions you steer into where opponents most often go wrong on the
  very next move, from your own games and stored evaluations (no engine). For each: caught N of M, the usual slip,
  what it wins, and the defence that holds. `GET`/`POST /users/traps-set`, new `traps_set` table (RLS)

### Added
- The swindle lens, the mirror of squeeze: once you are clearly losing (about −2), does each move set the opponent a
  real problem (the chaos measure at their rating), and was it sprung (they missed every safe reply)? Adds a **Fight**
  trait, a "Fighting back" card on You (comebacks from lost positions), and a list in Review
- The clock lens, time as style, scaled to each game's starting clock. Moves are found, rushed or missed when one move
  was clearly best, and quick, lingered or steady otherwise. Adds a **Clock** trait and a "Where your time went" card:
  time on critical vs easy moves, plus wins and losses on time
- `games.termination`, generated from the PGN header, so time-outs are counted without loading PGNs
- Lens contexts now carry the opponent's actual reply and the time spent on each move

### Added
- The squeeze lens: once you are clearly winning (about +2), does each move keep the advantage and leave the opponent
  little room? A move is "squeezed" (one or two replies still hold), "kept", or "gave air" (the edge drops by more
  than a pawn). It is measured in centipawns from stored engine lines, so it needs no re-analysis:
  `scripts/rescore_lenses.py --only-missing squeeze` scores games already analysed
- **Grip**, a sixth fingerprint trait: the share of your moves while winning that kept the grip
- You: a "Closing it out" card (web and phone) with the count and a link to the latest move that gave air
- Review: a "Closing it out" list with each squeezed or gave-air move and, for the latter, the move that kept it
  tight
### Security
- Next.js 15.5.27 → 15.5.28 for a critical advisory (GHSA-2464-fhr4-w9xw, remote code execution in the image
  optimizer with SVG). The remaining high advisories are in lint tooling and need a breaking ESLint upgrade

### Fixed
- Phone app (Expo): the board wrapped each row after seven squares, showing stripes instead of a checkerboard; it now
  has proper rank rows and file letters. The tab bar and header use the handoff's line icons and rook mark instead of
  text glyphs, and the tab labels are no longer clipped
- Phone app screens follow the handoff:
  - Home: latest-game card and Brilliant gauge
  - Review: header and round badges
  - Train: queue rows, with "Up next" then Start (Train also accepts a drill deep link)
  - Recap: streak card
  - Library: detail card with "Defend it yourself"
  - Play: warm-up card and bot chips
  - Onboarding: the four steps
  - Settings: labels and theme row
- Web Play: the Opponent prep card no longer displaces the Sarce bot card from its handoff position
- `docs/QA_V1.md` now covers every screen side by side, including the phone app

### Fixed
- Touch targets: every control is at least 44×44 to the touch on a phone. On the web, a `.tap` hit area covers the
  header Settings button, text links, steppers and compact toggles, and Recap's game bars fill their column. In the
  Expo app, `hitSlop` covers the back arrow and the steppers. The drawn sizes are unchanged. The QA record is in
  `docs/QA_V1.md`

### Added
- All games, from Review (`/games`): newest first, or most chaotic first (highest chaos peak, with real /
  calculated / unsound chaos counts). `GET /games?chaos=true` reads the top-scoring chaos rows in score order
  instead of a full history, so it stays fast as the library grows. Replaces PR #89, written for the removed `/lab`

### Added
- Shirov and Morphy reference values on the You axes (40 games each from the pgnmentor corpora, scored the same
  way as Tal): Shirov sacrifice 20 · chaos 36 · calm 95 · initiative 25; Morphy 22 · 31 · 90 · 22
- Your chaos map (You, web and phone): the opening positions you reach most often, how predictably opponents
  steer into each, your usual move, and the one sound move that sets opponents at your level the hardest problem
  (P_fail × stake, the Tal bot's measure). `GET`/`POST /users/chaos-map`, new `chaos_map` table (RLS). Moves that
  clearly ask more than your usual one become a Train drill, "chaos move in your opening"

### Fixed
- Games could stay "processing" forever: a database timeout while storing results, or an API restart mid-analysis,
  left them where nothing picked them up again. A transient storage error now sends the game back to pending (a
  real error marks it failed), and the API requeues interrupted games when it starts
- You took ~33 s (and sometimes hit the database statement timeout) on a 3,000-game library: sacrifice offers are
  parsed once per finished game and cached, the lens query reads only the three `details` keys it uses, and the
  heavy screens (Home, You, Library, Recap, Train) run off the event loop so one slow request no longer stalls
  the rest. Warm You load: ~2 s
- Library sacrifice glyphs: chaos verdicts were looked up per game and hit PostgREST's 1000-row cap, dropping
  most of them; they are now fetched for the tagged moves only
- Analysis past ~300 games: the baseline recompute put every game id in one URL (HTTP 414) and failed each
  analysis right after it was marked complete, skipping its chaos pass, find-rate rule and idea tagger; the ids
  are now paged and looked up in chunks. The chaos backfill also catches up the idea tagger
- Background sync drains a backlog continuously (5 s between batches) instead of sleeping `SYNC_MINUTES` after
  every 5 games

### Changed
- Brilliant needs a piece genuinely on offer (ADR 0007): attacked by something cheaper, or attacked and
  undefended. A defended piece only an equal could take no longer counts. Style vectors move to version 3; run
  `scripts/backfill_brilliant_find_rate.py` to re-apply the rules to stored games
- Licence: GNU AGPL-3.0 (was MIT), see ADR 0006 — open source and self-hostable; a modified version run as a
  service must share its source; compatible with python-chess (GPL-3.0+)

### Removed
- Style profile (review F11b): the one-word style label ("Sacrificial tactician", "Balanced improver", …) is gone.
  Its thresholds were hand-cut and never validated, and no screen showed it; style is the fingerprint on You
- The pre-v1 dashboard at `/lab` and the components only it used (ADR 0005); the Brilliant headline contract now
  checks Home; sign-in status moved to Settings

### Fixed
- Reference players: pgnmentor spells Tal "Mihail", so name matching failed and every Tal game counted him as
  White; matching now accepts surname plus first initial. The Tal axis values from the earlier run mixed in his
  opponents and were removed until the rerun
- Background analysis no longer freezes the API: move classification runs in a worker thread

### Added
- "Why this move?" in Review (web and mobile): the badge's reason, each Brilliant rule as a check with its
  number (sacrifice size, eval gap, already decided, a real choice, find-rate at your opponent's rating), the
  problem's P_fail ladder and safe replies, and lines to step through on a board — what you played and the reply,
  the engine's top lines, and a sacrifice that would have counted (`GET /games/{id}/moves/{ply}/why`)
- Multi-user sharing (M8): "Share link" on Summary and the library makes a read-only page at `/s/<token>` from a
  snapshot taken then (no opponent name, no private notes), listed and turned off in Settings → Shared links
  (migration `shared_links`, RLS); the background sync now serves every user who saved a username; mobile Summary
  shares through the system share sheet (`EXPO_PUBLIC_WEB_URL`)

### Fixed
- Settings no longer loses `aiAvailable` after saving a change (the AI help switch stayed usable)
- Shirov and Morphy as references: "<Master> in your openings" drills in Train from 1,995 Shirov and 208 Morphy
  positions (plus Tal's), rotated daily; the reference scripts take `--player` / `--key` and skip games the player
  isn't in; mobile You gains the Tal / Shirov / Morphy toggles
- `scripts/auth_smoke.py`: sign-in checked against a real Supabase Auth (throwaway user; token required, forged
  tokens refused, another user's data unreachable, settings on the right profile); passes on the local stack
- Positions from videos (PHASES 2.2–2.4): Train → Save a position takes a YouTube link and keeps the captions
  around that moment (or a pasted transcript when YouTube blocks the request); with Settings → "Video help (sent
  to AI)" on and Claude credentials on the server, Claude reads a board from a screenshot (FEN checked by
  python-chess) and summarises what was said. Saved positions are searchable (titles, notes, transcripts,
  summaries). Migration `position_sources`; new dependencies `anthropic`, `youtube-transcript-api`

### Fixed
- Background analysis no longer fails games when engines are starved: a 60 s engine protocol timeout (was 10 s),
  and the default `ANALYSIS_WORKERS` is half the CPU threads so the app and database stay responsive
- Tal's axis values from 40 games across his career, scored with him on the right side of the board (sacrifice
  18, chaos 36, calm 96, initiative 24; heuristic human model)
- Mobile: opponent prep (from Play) and Settings → Export journal through the system share sheet
- Mobile: Settings → Mascot and motion (Playful mascot, Motion: follow system / full / reduced), the quiet-week
  Home (numbers hidden, sleeping mascot, "End early") and the "Tracking paused" edge state, as on the web
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
- The dashboard no longer goes blank when a Tal player row exists without a benchmark: `maybe_single()`
  lookups now handle supabase-py returning `None` for no row (Tal benchmark, baseline, game lookups)
- Batch analysis loads the Maia-2 weights once per process instead of once per game
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
