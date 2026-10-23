# Sarce vs. the alternatives — scoring, pricing, positioning

**Status:** desk research plus one engine-free test (2026-10-23). Prices come from public listings and vary by
region and over time; check each site before quoting them. The head-to-head test on real games is
[BENCHMARK.md](./BENCHMARK.md) Parts A–B.

## 1. Pricing at a glance

| Tool | Free tier | Paid (monthly) | Paid (annual) | Notes |
| --- | --- | --- | --- | --- |
| **Lichess** | Everything: 40 deep server analyses per day, unlimited cloud/board analysis, Insights, Learn from your mistakes | — | — | "All features are free for everybody, forever"; Patron is a donation with no extra features ([features](https://lichess.org/features)) |
| **Chess.com** | 1 full Game Review per day | Gold ≈ $5.99 · Platinum ≈ $9.99 · Diamond ≈ $14.99 (third-party listing, Oct 2026; older 2023 figures ~$8/$12/$20) | Discounted | Unlimited review from Platinum. Coach explanations on every move, Insights and "Brilliant Moves" stats are Diamond ([plans](https://support.chess.com/en/articles/8562418-what-does-each-level-of-membership-get-me), [listing](https://www.stork.ai/tools/chess-com)) |
| **Aimchess** (sold by Chess.com, LLC) | Limited scouting and stats, 15 lessons per day | $9.99 (US App Store) | $71.99 (≈ $5.99/mo) | Six skill areas compared with your rating range ([App Store](https://apps.apple.com/us/app/aimchess-learn-chess-online/id1524941307)) |
| **DecodeChess** | 1 decoded game per day | $8.25 | $84 (≈ $7/mo); credit packs $15/60, $25/120 | Natural-language explanations from Stockfish NNUE; aimed at 800–1800 ([listing, Aug 2026](https://www.stork.ai/en/decodechess)) |
| **Chessigma** | Unlimited reviews, no sign-up | — | — | Free Chess.com-style review on Stockfish 17 ([overview](https://www.chess.com/blog/Alexander-PC/stop-paying-for-chess-analysis-the-4-best-free-tools-in-2026)) |
| **Chess DNA** | Listed as free | Not listed | — | 8-dimension skill radar, "world champion" style match, share cards ([App Store](https://apps.apple.com/app/id6762600434)) |
| **Maia Chess** | Free | — | — | Human-like bots, Maia analysis, puzzles, opening drills ([maiachess.com](https://maiachess.com)) |
| **Noctie** | Limited free play | ≈ $15 (per a competitor's comparison page, Sep 2026) | — | Human-like AI coach ([comparison](https://chessiverse.com/compare/chessiverse-vs-noctie)); unverified |
| **ChessBase '26** | — | — | One-off: €199.90 program · €249.90 Starter · €499.90 Premium | Desktop database; Style Report (aggressiveness, risk) aimed at opponent prep ([shop](https://shop.chessbase.com/en/products_id/9349)) |
| **Sarce** (proposal) | Style read, Brilliant %, fingerprint on recent games; full history via your own Sarce Node; self-host free (AGPL) | Plus ≈ $4 | ≈ $36 | Coach ≈ $15 for 10 students ([SUSTAINABILITY.md](./SUSTAINABILITY.md)) |

**What the prices say:**

- **Lichess sets the floor at free.** Analysis alone can't be what Sarce charges for.
- **Paid analysis clusters at $6–15 a month.** Aimchess, DecodeChess, Chess.com Platinum and Diamond, and Noctie
  all sit there.
- **Sarce Plus at about $4 undercuts every paid tool.** That fits a companion that people use alongside a
  Chess.com membership, not instead of one.
- **Chess.com keeps its own "Brilliant Moves" stats behind Diamond, its top tier.** That suggests players value a
  Brilliant history, and Sarce gives it away free (principle 1).

## 2. Scoring models side by side

| | Lichess | Chess.com | Aimchess | Chess DNA | DecodeChess | Sarce (today) |
| --- | --- | --- | --- | --- | --- | --- |
| Engine | Stockfish 19 | Stockfish (cloud) | Engine-based | Stockfish | Stockfish NNUE | Stockfish 18, node-limited MultiPV |
| Scale | Win% from centipawns (published) | Expected points, **rating-aware** (model private) | Not published | Not published | — | Centipawn loss (Phase 1); EP for chaos |
| Move labels | Inaccuracy / Mistake / Blunder by win-chance drop | Best · Excellent ≤ 0.02 · Good ≤ 0.05 · Inaccuracy ≤ 0.10 · Mistake ≤ 0.20 · Blunder > 0.20 EP; plus Brilliant, Great, Miss, Book | Area scores | Mistake tags | Explanations, not labels | Best ≤ 0 · Excellent ≤ 25 · Good ≤ 50 · Inaccuracy ≤ 100 · Mistake ≤ 200 · Blunder > 200 cp; plus Brilliant, Miss |
| Accuracy | Published: per move `103.1668·e^(−0.04354·ΔWin%) − 3.1669`; game = mean of volatility-weighted and harmonic means | CAPS2 (private) | — | — | — | Not a headline (by design) |
| Brilliant | No such tier | "A good piece sacrifice", best or nearly best, not already completely winning; **more generous for newer players** | — | — | — | Real offer (attacked by cheaper or undefended, ≥ minor) + eval within 0.25 + not already winning + **hard to find** (Maia ≤ 20% at the rating) |
| Human model | No | Rating enters EP | Compares with your range | — | — | **Maia-2**: chance a human at each rating plays each move |
| Style | Insights (stats you filter) | Insights (Diamond) | Six skill areas | Radar + champion match | — | Nine traits, chaos lens, reference players, intent journal |
| Uncertainty shown | No | No | No | No | No | No (planned, [STYLE_SCIENCE_PLAN](./STYLE_SCIENCE_PLAN.md) S7) |

Sources: [Lichess accuracy](https://lichess.org/page/accuracy), [Chess.com classification](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc),
`apps/api/app/services/move_classifier.py`, `apps/api/app/services/brilliant.py`.

## 3. Test: the same moves through each scoring model

`apps/api/scripts/compare_scoring_models.py` applies each tool's published rules to the same eval drops. It needs
no engine. Chess.com's EP model is rating-aware and private, so its column uses the Lichess win curve as a
**proxy** for their EP. It is not Chess.com's actual output.

| Before → after (cp) | Loss | Win% drop | Lichess judgement | Lichess move accuracy | Chess.com tier (EP proxy) | Sarce tier (cp) |
|---|---|---|---|---|---|---|
| +0 → −100 | 100 cp | 9.1 | Inaccuracy | 66% | Inaccuracy | Inaccuracy |
| +300 → +200 | 100 cp | 7.5 | Inaccuracy | 71% | Inaccuracy | Inaccuracy |
| +600 → +500 | 100 cp | 3.8 | — | 84% | Good | **Inaccuracy** |
| +900 → +800 | 100 cp | 1.5 | — | 94% | Excellent | **Inaccuracy** |
| +0 → −200 | 200 cp | 17.6 | Blunder | 45% | Mistake | Mistake |
| +500 → +300 | 200 cp | 11.2 | Mistake | 60% | Mistake | Mistake |
| +800 → +400 | 400 cp | 13.7 | Mistake | 54% | Mistake | **Blunder** |
| +1000 → +600 | 400 cp | 7.4 | Inaccuracy | 71% | Inaccuracy | **Blunder** |
| −300 → −400 | 100 cp | 6.2 | Inaccuracy | 75% | Inaccuracy | Inaccuracy |
| −600 → −900 | 300 cp | 6.4 | Inaccuracy | 75% | Inaccuracy | **Blunder** |
| +150 → −150 | 300 cp | 26.9 | Blunder | 29% | Blunder | Blunder |
| +0 → −40 | 40 cp | 3.7 | — | 85% | Good | Good |
| +400 → +340 | 60 cp | 3.6 | — | 85% | Good | **Inaccuracy** |

**Result:** Sarce agrees with the Chess.com proxy on **7 of 13** cases. All six disagreements are positions that
were already decided (|eval| ≥ +4), where Sarce labels the move harsher. Losing a pawn's worth at +9 is
"Inaccuracy" in Sarce and "Excellent" on Chess.com. Players who compare the two will see Sarce as stricter, and
for a reason that has nothing to do with style.

This is review finding F5.3 shown concretely. It's fixed by [STYLE_SCIENCE_PLAN](./STYLE_SCIENCE_PLAN.md) S5
(classification by EP loss, fitted by rating and time control).

## 4. Brilliant: the benchmark to copy

Chessigma publishes a [Brilliant agreement benchmark](https://www.chessigma.com/benchmarks/brilliant) against
Chess.com, last updated 31 July 2026. It used 100 Chess.com brilliants from 2020–2026 across bullet, blitz and
rapid, and reported two numbers per tool:

| Tool | Brilliants caught (of 100) | Its badges confirmed by Chess.com | Over-calls per 1,000 non-brilliant moves |
| --- | --- | --- | --- |
| Chessigma | 93 | 95% | 0.7 |
| Chessiro | 90 | 75% | 2.3–4.2 across these four tools |
| WintrChess | 45 | 73% | |
| Chessitup | 41 | 62% | |
| Chesskit | 23 | 51% | |

Chessigma publishes this about its own tool, and its detector internals aren't public. The page gives one
over-call range for the other four tools, not a figure for each.

**What it means for Sarce:**

- **Use the same method in benchmark Part B:** catch rate, confirmation rate and over-calls per 1,000 moves.
  Add one column the others can't report: *which Sarce clause failed* for each Chess.com Brilliant it didn't
  call.
- **Sarce should not aim for 93/100.** Its Brilliant is stricter on purpose. It needs a real offer, and a move
  that's hard to find for *your* rating. Chess.com's is more generous for newer players. A lower catch rate with
  a high confirmation rate (few over-calls) is the right profile. The "almost Brilliant" copy explains the gap.
- **One difference no other tool has:** Chess.com and the look-alike tools label *what* happened. Sarce's
  find-rate clause measures *how hard it was for a human at that rating*. That's the defensible part of Sarce's
  Brilliant.

## 5. Where Sarce stands

| Dimension | Strongest alternative | Sarce today | Sarce after the plan |
| --- | --- | --- | --- |
| Raw engine analysis | Lichess (free, Stockfish 19) | Same engine, slower, server cost | Cache + tiered search (S12); no need to win here |
| Move labels players trust | Chess.com Game Review | Centipawn thresholds; harsh in decided positions (§3) | EP by rating and time control (S5) |
| Brilliant | Chess.com (Diamond stats) | Stricter, explains itself ("Why this move?") | Recalibrated by band (S9) + "almost Brilliant" + Part B numbers |
| Skill profile | Aimchess, Chess DNA (radars) | Nine traits, raw fractions, no intervals | 4–6 validated constructs as percentiles with read states (S6–S8) |
| Human difficulty | Maia Chess (bots and analysis) | **Chaos lens, validated** (Brier 0.155) | Maia-3, blitz and rapid validated (S4); Originality and difficulty-adjusted performance (S10) |
| Style identity | Chess DNA "champion match" (method unpublished) | Reference dots (not comparable yet, F3) | Learned style embeddings, "distance to Tal" (S14) |
| Intent vs reality | Nobody | **Intent journal** | Grounded commentary (S13) |
| Honest uncertainty | Nobody | — | **S7: the first to show it** |
| Price | Lichess (free); paid tools $6–15/mo | Not launched | Free core + about $4 Plus |

**Positioning:** *"The engine shows truth; Maia shows humans; Sarce shows you."*

- Don't compete on analysis. Lichess gives it away, and Chessigma copies Chess.com's review for free.
- Compete on what nobody publishes or validates:
  - human difficulty (chaos, originality, find rate);
  - intent against reality;
  - honest uncertainty;
  - a style measured, not guessed.
- The radar products (Aimchess, Chess DNA) are the nearest rivals for the "you" story. Neither publishes how
  their scores are made. **An open, validated method is Sarce's edge** (S8, S15).

## 6. What to do with this

1. **Do S5 first among the scoring changes.** §3 shows the centipawn labels will look wrong next to Chess.com in
   one of the most common situations: converting a won game.
2. **Run benchmark Part B with the Chessigma-style metrics, plus Sarce's clause column.** Publish both numbers.
3. **Keep Plus below the $6–15 paid cluster,** and keep Brilliant history free. Chess.com charges Diamond for it,
   which makes it a good free hook.
4. **Re-check prices before launch.** Most of these figures come from listings, not first-party price pages.
