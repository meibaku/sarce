# Implementation plan — the October 2026 review

Every suggestion in [REVIEW_2026-10.md](./REVIEW_2026-10.md) and its companion docs ([BENCHMARK.md](./BENCHMARK.md),
[COMPUTE.md](./COMPUTE.md), [LEGAL.md](./LEGAL.md), [SUSTAINABILITY.md](./SUSTAINABILITY.md), ADR 0008), turned into
work items with an order, a size, dependencies, and who has to decide what. Written 2026-10-23, after #159.

**Size:** S ≈ one PR under a day · M ≈ one or two PRs · L ≈ several PRs or long compute.
**Needs:** **ADR** (changes a domain invariant or a metric's meaning) · **engine** (hours of Stockfish) ·
**data** (a download to approve) · **you** (a decision, an account, money or a message only the owner can send).

## Done

| Item | What | PR |
| --- | --- | --- |
| F12 | Game results inverted for a third of Chess.com games; PGN `[Result]` is now the source of truth | #156 (v1.2.1) |
| F2 | Sacrifice trait counts real sacrifices only; axis per 1,000 moves; references rescored board-only | #158 |
| F4 | Wilson ranges, rolling 20-game trend, "up/down" only when ranges separate, traits dashed under 30 events | #159 |
| §3.6 (part) | `feat/chaos-sorted-games` superseded and closed (#89 → #139) | #139 |

**What F2 and F4 revealed** (shapes the order below):

- Under rule v3 (find-rate plus real offer) your Brilliant % is **0.01%** (range 0.00–0.06%). That's about one in
  9,000 moves, so the 6–10% band is out of reach. **F6 moves to the front.**
- With the strict test, Tal (5 per 1,000) is still below Morphy (16) on only 7 events in 40 games, so the
  references need **F3** before the axis says anything.

## Phase 1 — Measure correctly (engineering only, no outside decisions)

Order matters: F6 and F1 change what Brilliant and chaos mean, and everything later builds on them.

| # | Item | Approach | Size | Needs | Depends on |
| --- | --- | --- | --- | --- | --- |
| 1.1 | **F6a: benchmark runner** | `ReferenceService.process_tal_benchmark()` runs the same pipeline as a player's games, including the `BrilliantFindRate` post-pass | S | — | — |
| 1.2 | **F6b: re-measure Brilliant under v3** | Run 1.1 on ≥ 200 Tal games, with a game-level bootstrap interval. Also report the distribution of clause failures for your games ("which clause stops Brilliant at 200 level?") | M | engine | 1.1 |
| 1.3 | **F6c: the band and a personal next band** | If Tal is near 6–10%, keep it as "Tal tier". Otherwise change it via ADR (the band is CI-enforced). Either way, add a **next band**: your interval's upper bound plus one step, shown on the gauge and Settings | S–M | ADR if the band changes | 1.2, F4 ✓ |
| 1.4 | **F1: rating → model Elo** | `rating_to_model_elo(source, time_control, rating)`, versioned, from published Chess.com↔Lichess tables, used everywhere a rating meets the human model (lens ladder, find-rate rung, chaos map rung). Bump lens and style-vector versions, then rescore | M | data (comparison table) | — |
| 1.5 | **F11a: find-rate uses the mover's rating** | Use the mover's own converted rating at the 100-point rung `elo_ladder` already adds, not the opponent's at 400-point rungs | S | — | 1.4 |
| 1.6 | **F5: the Brilliant rule vs its spec** | ADR 0009 decides: (a) "not forced" means *reasonable alternatives existed* vs legal-move count; (b) exclude lost positions with the same decided EP band as chaos; (c) classify by **EP loss**, not raw centipawns. Then style vector v4, `backfill_brilliant_find_rate`, and golden tests updated | L | ADR, engine (golden) | 1.2 (to see the effect) |
| 1.7 | **F8: one unit across lenses** | Move squeeze/swindle/clock/prophylaxis thresholds to EP (chaos plan rule 4), or document per lens why centipawns. Rescore with `rescore_lenses.py` (no engine) | S–M | — | — |
| 1.8 | **F7: winner's curse** | Your traps and the trap atlas rank by a shrunk estimate (Wilson lower bound from `uncertainty.py`) and show "seen n times" | S | — | F4 ✓ |
| 1.9 | **F10a: overlapping traits** | Correlation matrix of the nine traits across your weeks and the references. Merge or drop pairs with \|r\| > 0.8 (Initiative and Chaos are the likely pair). Calm's ceiling: rescale or redefine | M | ADR if a trait is dropped | — |
| 1.10 | **F11b: style label** | Delete the hand-cut label in `style_profile.py`, or replace it with percentile traits once 3.3 exists | S | — | (3.3) |

## Phase 2 — Make the references and lenses trustworthy (compute and data)

| # | Item | Approach | Size | Needs | Depends on |
| --- | --- | --- | --- | --- | --- |
| 2.1 | **F3a: rescore references** | Same human model as your data, 100–200 games each until the bootstrap intervals are narrower than the gaps drawn, intervals stored next to each value, dots labelled "Tal (classical)" | L | engine (many hours) | 1.4, 1.6 |
| 2.2 | **F3b: contrasting references** | Petrosian, Karpov and Carlsen: if Petrosian scores like Tal on Chaos, the axis isn't measuring style (a discriminant check) | M | data (PGN downloads), engine | 2.1 |
| 2.3 | **F9: validate every lens** | M4-style test on the Lichess database for each lens's falsifiable prediction (REVIEW §F9 table); chaos re-run for 3+0, 10+0 and the app's node budget | L | data, engine | 1.7 |
| 2.4 | **F10b: percentile traits** | Each trait as a percentile within rating band × time control from Lichess population tables (positions and counts only, no names); "Chaos 80" means above 80% of your band | L | data, engine | 2.3, 1.9 |

## Phase 3 — Product (from REVIEW §3–§6)

| # | Item | Approach | Size | Needs | Depends on |
| --- | --- | --- | --- | --- | --- |
| 3.1 | **Time to first read (§3.2)** | On sign-up, analyse the newest 20 games first (the queue is already newest-first; make sign-up import feed it in that order), then backfill. Measure the time | S | — | — |
| 3.2 | **One focus a week (§3.3)** | Home picks one trait each week (the ADR 0003 focus picker), with a target from your interval, and says how this week moved it. Overlaps 3.6 | M | — | F4 ✓ |
| 3.3 | **Brilliant disagreements (§4)** | "Sarce Brilliant" line under the badge; "almost Brilliant" naming the one failed clause ("Why this move?" has the checklist); a "Chess.com called this Brilliant" button storing (move, clause) as calibration data (new table, RLS); a public definition page with examples | M | — | 1.6 |
| 3.4 | **Layer on top (§5)** | Session-read notification after auto-sync; every Review move links to the same move on Chess.com or Lichess; Play stays training-only (already). **Lichess study export** needs Lichess OAuth | S + M | you (Lichess OAuth app) for the export | — |
| 3.5 | **Style cards (§6.1)** | Shareable image of fingerprint, best Brilliant and favourite chaos move, with the mascot; reuses share-link stripping | M | — | 2.1 (honest refs) |
| 3.6 | **Weekly quests (§6.2)** | "Play like Tal this week": one trait, interval-based target, three drills from your games, a recap verdict | M | — | 3.2 |
| 3.7 | **Opponent-aware chaos (§6.3)** | Scouting plus the chaos map: the line where *this* opponent goes wrong most | M | — | — |
| 3.8 | **Per-time-control fingerprints (§6.6)** | Bullet-you and rapid-you side by side, and the gap | S–M | — | F4 ✓ |
| 3.9 | **Chaos budget (§6.7)** | Risk taken vs paid, per game: "0.4 EP spent on chaos, 0.7 back" | S | — | 1.7 |
| 3.10 | **Style twin (§6.4)** | Closest historical player, with uncertainty | M | — | 2.1, 2.4 |
| 3.11 | **Localisation (§6.8)** | Extract copy to message files; Kiswahili first, then Spanish, Hindi, Russian | M + translation | you (translators/review) | — |
| 3.12 | **Voice/animated recap (§6.9)** | 30-second mascot recap | M | you (voice choice) | — |
| 3.13 | **Coach view (§6.5)** | Students side by side, drills, notes; the Coach tier | L | you (pricing) | 5.4 |

## Phase 4 — Compute and operations (from BENCHMARK, COMPUTE, ADR 0008, REVIEW §3.4–3.5)

| # | Item | Approach | Size | Needs | Depends on |
| --- | --- | --- | --- | --- | --- |
| 4.1 | **Benchmark A: Lichess comparison** | Automated pipeline and metrics as in BENCHMARK.md Part A | M | data, engine | 1.6 |
| 4.2 | **Benchmark B: Chess.com comparison** | Labels collected by hand; 3.3's button supplies them continuously | M | you (labelling time) | 3.3 |
| 4.3 | **Benchmark C0–C3: cost** | Measure C0. C1: pre-load the Lichess evaluation database (CC0) into `position_evals`. C2: tiered search (full MultiPV only on candidate moments; ≥ 95% verdicts identical). C3: recent-first (= 3.1) | M–L | data (large download), engine | — |
| 4.4 | **Decide ADR 0008** | Shared cache → player's device (Sarce Node) → browser → cloud, decided on 4.3's numbers. It narrows "Stockfish server-side only" | S (decision) | ADR, you | 4.3 |
| 4.5 | **Operations (§3.4)** | Queue metrics (depth, age, failures) and a "Settings: analysis is N games behind" line are engineering-only. Error tracking and nightly backups depend on hosting | S + M | you (error-tracking service, hosting) | 5.1 |
| 4.6 | **Dependencies (§3.5)** | The breaking `eslint-config-next`/ESLint 10 upgrade clears the remaining high advisories; then Next 16 and TypeScript Dependabot PRs; one housekeeping PR a week | M | — | — |
| 4.7 | **Stale branches (§3.6)** | `feat/background-import-jobs` and `fix/service-role-grants` (old #55/#54): review, then merge or close | S | you (close or merge) | — |

## Phase 5 — Launch: deploy, legal, sustainability (owner decisions)

| # | Item | Approach | Size | Needs | Depends on |
| --- | --- | --- | --- | --- | --- |
| 5.1 | **Hosted beta (§3.1)** | API plus Stockfish on a dedicated server, managed Supabase in a region chosen for PDPC transfers, web on a static/edge host | M | you (provider, region, budget, accounts) | 4.4 (where analysis runs) |
| 5.2 | **Privacy before launch (LEGAL §4)** | Engineering: privacy notice page, minimum-age gate with guardian consent, in-app **export and delete** (including derived data), retention expiry for cached snippets, processor list | M | you (notice text sign-off) | — |
| 5.3 | **Legal checklist (LEGAL §6)** | CLA or DCO enforced on PRs; TRADEMARKS.md; source-offer text for binaries are engineering. Registering "Sarce", emailing legal@chess.com and PDPC registration are owner actions | S + owner | you | — |
| 5.4 | **Tiers and payments (SUSTAINABILITY)** | Free / Plus / Coach after the pilot shows what people value; the style read is never paywalled; payment provider and tax setup later | L | you | 4.2, 5.5 |
| 5.5 | **Pilot (Benchmark D)** | 5–10 real players, the style-pilot protocol | M | you (recruiting), 5.1 | 5.1 |

## Suggested order (revising REVIEW §7)

| Step | Work | Who |
| --- | --- | --- |
| 1 | 1.1 → 1.2 (Tal under v3 and your clause failures), 1.8, 1.7, 4.7 review | Claude; engine time on your machine |
| 2 | 1.3 (band decision) and 1.4–1.5 (rating mapping) | Claude drafts the ADR; **you approve the band** |
| 3 | 1.6 (ADR 0009 and rule v4), 1.9, 3.1, 3.8 | Claude; **you approve ADR 0009** |
| 4 | 2.1–2.2 references (long engine runs, downloads approved), 4.6 | Claude; **you approve downloads** |
| 5 | 3.3 disagreement UI, 3.2/3.6 focus and quests, 4.3 benchmark C | Claude |
| 6 | 4.4 ADR 0008, 5.1 hosted beta, 5.2 privacy flows | **You choose hosting**; Claude implements |
| 7 | 5.5 pilot, 3.5 style cards, 4.1–4.2 benchmarks | **You recruit**; Claude builds |

Not before Phase 2 is done: any new trait, style twin (3.10), or percentile claims (2.4). The review is explicit
that new measures wait for validation (F9).

## Decisions only you can make

1. Keep or change the 6–10% band once Tal is re-measured (1.3).
2. ADR 0009's three Brilliant clauses (1.6).
3. Approving downloads: Chess.com↔Lichess rating tables, contrasting players' PGNs, Lichess database and evaluation
   dump (1.4, 2.2, 2.3, 4.3).
4. Hosting provider, region and budget (5.1); error-tracking service (4.5).
5. Merge or close the two stale branches (4.7).
6. Legal: trademark, the email to Chess.com, PDPC registration, CLA vs DCO (5.3).
7. Lichess OAuth app for study export (3.4); translators (3.11); pricing (5.4).
