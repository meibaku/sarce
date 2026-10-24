# Phase 3 plan: product (implementation plan items 3.1–3.13)

Detail for Phase 3 of [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md). Written 2026-10-24, after Phase 1 merged
(#161–#170). Ground rules are the usual ones (AGENTS.md):
- PRs of about 800 lines or fewer, from `staging`, with CHANGELOG entries.
- New tables get RLS, in a new migration.
- No punitive copy: `philosophy-check`.
- Post-game only.
- Web and Expo ship together, unless a step says otherwise.

## What can start now, and what waits

| Wave | Items | Why this wave |
| --- | --- | --- |
| **A: no engine, no outside decisions** | 3.1, 3.8, 3.9, 3.4a, 3.3 | Built on data already stored. They don't compete with the Tal run or the analysis queue for CPU |
| **B: builds on A** | 3.2, then 3.6, then 3.7 | Weekly focus feeds the quests. Opponent-aware chaos needs the chaos map engine, so it runs after the Tal run |
| **C: waits on Phase 2** | 3.5, 3.10 | Style cards and the style twin show reference players; they need honest references (2.1) and percentiles (2.4) |
| **D: waits on you** | 3.4b, 3.11, 3.12, 3.13 | A Lichess OAuth app, translators, a voice, pricing (5.4) |

Suggested PR order:

| # | Item | PR | Lines (est.) |
| --- | --- | --- | --- |
| 1 | 3.1 | Time to first read | ~250 |
| 2 | 3.8 | Per-time-control fingerprints | ~450 |
| 3 | 3.9 | Chaos budget | ~350 |
| 4 | 3.4a | Links to the site + session read | ~400 |
| 5 | 3.3 part 1 | Brilliant disagreements: "almost Brilliant" and the definition page | ~600 |
| 6 | 3.3 part 2 | "Chess.com called this Brilliant" (new table) | ~400 |
| 7 | 3.2 | One focus a week | ~600 |
| 8 | 3.6 | Weekly quests | ~700 |
| 9 | 3.7 | Opponent-aware chaos | ~600 |
| 10+ | 3.5, 3.10, 3.4b, 3.11–3.13 | When their gates open | — |

---

## 3.1 Time to first read

**Goal:** a new player sees their first style read within minutes of connecting an account, not after their whole
history imports.

**Today:**
- The analysis queue is already newest-first (`analysis.analyze_pending` orders by `played_at desc`).
- Import fetches every Chess.com monthly archive before analysis starts, so a long history delays the first game.

**Build:**
1. **Import:** `SyncService.sync` imports the newest archive month first, then queues one analysis job
   (`job_queue.queue_analysis`) right away. Older months follow in the background.
2. **Lichess:** the newest 20 games are fetched first, then the rest, with the same queueing.
3. **Measuring it:**
   - Migration `games.analysed_at timestamptz`, set when analysis completes.
   - Migration `profiles.first_read_at`, set the first time a game completes for that owner.
   - The time from sign-up to first read appears in `/users/sync-status` and as a one-off script.
   - The goal is a first read in under 5 minutes for a 1,000-game history.
4. **Onboarding:** the "2 more moments still being scored…" step polls sync status, so it shows the real first
   game rather than waiting for the backfill.

**Tests:**
- Import order (newest month first).
- The job is queued after the first batch.
- `first_read_at` is set once.

---

## 3.8 Per-time-control fingerprints

**Goal:** bullet-you and rapid-you side by side, and the gap between them. Your 1+0 and 10+0 games differ, so one
fingerprint blurs two players.

**Build:**
1. **API:** `you.trait_values` already works for any set of moves. Add `fingerprint_by_class` to the You payload:
   - per time class (`time_class()`: bullet, blitz, rapid), the nine traits with event counts;
   - each value gated by MIN_EVENTS (review F4), with a Wilson range for the rate traits;
   - `gap`: the three traits that differ most between your two most-played classes, and only where the ranges
     don't overlap (uses `uncertainty.direction`).
2. **Web:** You gets a "By time control" card: two columns of trait bars, plus a gap sentence such as "In bullet
   you set problems twice as often; in rapid you hold more." It uses the existing time-control split's labels.
3. **Expo:** the same card on the You tab.

**Copy rule:** differences are styles, never "worse at bullet" (philosophy-check).

**Tests:**
- Per-class gating.
- The gap only when the ranges separate.

---

## 3.9 Chaos budget

**Goal:** per game, how much risk you took and how much it paid, for example "0.4 EP spent on chaos, 0.7 back".
This needs F8, which is merged: every lens is in expected points.

**Build:**
1. **Pure function** `chaos_budget(lens_rows)` in a new `services/budget.py`:
   - spent = Σ objective cost of your moves that set a problem (chaos verdicts with `objective_cost`);
   - back = Σ EP your opponents dropped on the replies that followed (survival/swindle `fell` plus the reply's EP
     loss);
   - net = back − spent.
   - Stored lens details only, no engine.
2. **API:** Summary gains `budget`, and You gains the last 20 games' budget (a rolling sum).
3. **Web:**
   - Summary shows one line under the moments: "Chaos budget: 0.4 spent · 0.7 back", in neutral tone even when
     net is negative.
   - You shows a small 20-game sparkline.
4. **Expo:** the Summary line.

**Tests:** the budget arithmetic on fixtures, and that unknown replies are excluded.

---

## 3.4a Layer on top: links to the site, and the session read

**Goal:** Sarce sits on top of Chess.com and Lichess rather than replacing them.

**Build:**
1. **Links to the move:**
   - Every Review move links to the same move on its site.
   - Chess.com: `game.external_id` is the game URL; append `?move=N`. Check the parameter against a live game
     before shipping; fall back to the plain game URL.
   - Lichess: `https://lichess.org/{id}#{ply}`.
   - The link sits next to the existing "Open in Lichess analysis ↗".
2. **Session read:** after an auto-sync brings in new games and they finish analysing, Home shows a one-line
   banner, for example "Your last session: 6 games, 2 that felt like you, 1 real problem set". It rests on games
   analysed since the last visit, kept in `localStorage` (web) or `AsyncStorage` (Expo).
3. **No push notifications in this wave.**
   - Web Notifications need a permission prompt.
   - Expo push needs a push service account.
   - Both are listed under decisions below.

**Tests:**
- Move-link building for both sites.
- The session window.

## 3.4b Lichess study export (waits on you)

A "Send to a Lichess study" button on Review: your moments as chapters, with the engine line and your intent
note. It needs a **Lichess OAuth app** (client id, redirect URI), registered by you. Scope: `study:write` only. The
token is held per user, encrypted, and revocable from Settings.

---

## 3.3 Brilliant disagreements

**Goal:** when Sarce and Chess.com disagree about Brilliant, explain it rather than look wrong, and learn from it.
This needs rule v4, which is merged (ADR 0009).

**Part 1 (no new table):**
1. **"Almost Brilliant":**
   - A move that passes every clause but one gets a `near_brilliant` marker naming that clause.
   - It is computed in `BrilliantFindRate.rejudge` from the same clauses and stored in `game_moves.signals`
     (`near_brilliant:sound`, …), so no migration is needed.
   - Review shows "Almost Brilliant: it gave a little too much (0.05 EP)", linking to Why this move?.
2. **Badge line:** under every `!!`, a short "Sarce Brilliant" label linking to the definition page.
3. **Definition page** `/brilliant`, public and needing no account:
   - the five clauses in plain words;
   - the thresholds, read from the API so they can't drift;
   - three worked examples from the golden test games.
4. **Expo:** the "almost" line on Review.

**Part 2 (new table):**
1. **Migration `brilliant_reports`:**
   - columns: id, owner_id, game_id, ply, source ('chess_com'), failed_clause, created_at;
   - RLS: the owner can insert and read their own rows;
   - no free text, so no moderation is needed.
2. **Button:** "Chess.com called this Brilliant" on Review for any move that isn't `!!`. It stores which clause
   Sarce's rule failed and thanks the player. It is never shown as "Sarce was wrong".
3. **Use:** a script summarises reports by clause. This is the calibration data that Benchmark B (4.2) needs.

**Tests:**
- Exactly one clause failing yields the marker.
- RLS (owner only) in the migration test.
- The definition page renders the API thresholds.

---

## 3.2 One focus a week

**Goal:** Home picks one trait for the week, sets a target from your own range, and says how the week moved it.

**Build:**
1. **Picker:**
   - It takes the trait with the most room. That is the lowest percentile of the trait within your own last 12
     weeks, among traits with enough events.
   - Brilliant is never the focus. It stays the headline (ADR 0001; ADR 0003's rule that a focus changes emphasis,
     not the headline, carries over).
   - You can override it from the existing weekly focus (`user_focus`, kind `weekly`, which gets new values: the
     nine traits).
2. **Target:** your trait range's upper bound for the last four weeks, so it is reachable and rests on your own
   data (review F4).
3. **Home card:** "This week: Grip. Last week 0.78; aim for 0.84". At the week's end the Recap says whether it
   moved, using `uncertainty.direction`; within noise it says "held".
4. **API:** `home.weekly_focus`; Recap's `lastFocus` reads it.
5. **Expo:** the same card.

**Tests:**
- The picker skips gated traits.
- The target comes from the range.
- The verdict uses separated ranges only.

## 3.6 Weekly quests (after 3.2)

**Goal:** "Play like Tal this week": one trait, a target, three drills from your own games, and a Recap verdict.

**Build:**
1. **Quest:** the 3.2 focus plus a reference player whose value on that trait is far from yours.
   - The reference value comes from `reference_axes`.
   - The player is labelled "Tal (classical)" and flagged as provisional until 2.1 lands.
2. **Drills:** three positions from your games where that trait's lens fired, for example squeeze chances you let
   go for Grip. They are queued in the existing Train queue (`drills`, `train.py`) with source `quest`.
3. **Verdict:** the Recap gets a quest line: done, held or try again. It reads from 3.2's verdict, never "failed".

**Tests:**
- Drill selection per trait.
- The quest rotates weekly.

## 3.7 Opponent-aware chaos (engine; after the Tal run)

**Goal:** before a rematch, the line where *this* opponent goes wrong most.

**Build:**
1. **Positions:** the scouting report (`scouting.py`, public games, no names stored beyond the username you
   typed) lists the opponent's most frequent opening positions.
2. **Chaos:** for each of those positions, the chaos map engine (`chaos_map.chaos_move`) runs at the opponent's
   converted rating (`rating_map`).
3. **Their history:** the opponent's own past replies in that position. A position where they went wrong before
   ranks first.
4. **Screen:** Prep gets a "Where they go wrong" list with the line, your chaos move, P_fail at their rating, and
   their actual record.
5. **Rules:**
   - Post-game only and public games only.
   - Never during a game. The report is built on request, like scouting is today.

**Tests:**
- The ranking with their history.
- The rating conversion is used.

---

## Waits on Phase 2

- **3.5 Style cards:** a shareable image of your fingerprint, best Brilliant and favourite chaos move, with the
  mascot. It reuses the share-link path (`sharing.py`, token, revocable) and renders the image client-side on a
  canvas (no new dependency). It waits on 2.1, so the reference dots on the card are honest.
- **3.10 Style twin:** the closest historical player by trait distance, with a bootstrap range, saying "closest:
  Shirov, but Tal is within the range" when they overlap. It needs 2.1 (references) and 2.4 (percentiles).

## Waits on you

| Item | What's needed | Suggested default |
| --- | --- | --- |
| 3.4b | A Lichess OAuth app (client id, redirect URI) | Register "Sarce" at lichess.org/account/oauth/app with `study:write` |
| 3.4 push | Whether Sarce may send notifications | Web: off by default, opt-in from Settings. Expo: Expo's push service (free); opt-in |
| 3.11 | Translators or reviewers for Kiswahili, then Spanish, Hindi, Russian | Extract copy to message files first (engineering, no translator needed); add languages as reviewers sign up |
| 3.12 | A voice for the 30-second recap | Start with captions only (mascot plus text); add a voice later |
| 3.13 | Pricing (5.4), after the pilot | Not before the pilot (5.5) |

## Out of scope for Phase 3

- New traits: they wait for Phase 2's validation (F9).
- Percentile claims (2.4).
- Changing Brilliant % as the headline (ADR 0001).
