# Sarce — Sustainability (how Sarce pays for itself)

**Status:** proposal (2026-10-22). Prices are hypotheses for the benchmark pilot (Part D) to test, not
decisions.

## Principles

1. **The style read is never paywalled.** Every player gets their Brilliant %, fingerprint and game reads on
   recent games for free. Paying buys *speed, depth and convenience*, not the mirror itself
   ([PHILOSOPHY.md](./PHILOSOPHY.md)).
2. **Free should cost Sarce almost nothing.** The free tier runs on the shared cache and on the player's own
   device ([COMPUTE.md](./COMPUTE.md), ADR 0008). That keeps it sustainable at any scale.
3. **Open source is the moat, not the weakness.** AGPL means a competitor who hosts a modified Sarce must
   publish their changes. The brand, the hosted convenience and the community stay yours ([LEGAL.md](./LEGAL.md)).
4. **No ads, no selling data, no dark patterns.** No upsells written as nags; the coaching tone applies to
   pricing pages too.

## Tiers (hypothesis)

| | **Free** | **Sarce Plus** | **Coach** |
| --- | --- | --- | --- |
| Who | Everyone | Players who want everything done for them | Coaches, clubs, schools |
| Analysis | Recent games; full history via your own Sarce Node or browser | Full history analysed in the cloud; new games read within minutes | Plus for every student |
| Style read, Brilliant %, fingerprint | ✅ | ✅ | ✅ |
| Phone without a desktop | Recent games | Everything | Everything |
| Opponent prep, scouting | Limited (e.g. 3 per month) | Unlimited | Unlimited |
| Reference players, "Tal in your openings" | Tal | All references | All |
| Journal export, shared style cards | Basic | Full (animated recap, PDF journal) | Full |
| Coach dashboard: students' fingerprints, assign drills | — | — | ✅ |
| Self-host | Always free (AGPL) | — | — |

**Price anchors to test in the pilot:**

- Plus: about **$4/month or $36/year**, with regional (purchasing-power) pricing. In Tanzania and similar
  markets, a lower local price paid by mobile money.
- Coach: about **$15/month for up to 10 students**.

Chess.com and Lichess anchor what players expect. Lichess is free and donation-funded; Chess.com sells
memberships. Sarce Plus should sit well below a Chess.com membership, because it's a companion, not a
replacement.

## Other income

- **Supporters:** turn on GitHub Sponsors (`.github/FUNDING.yml` is ready, just commented out) and offer a
  small in-app supporter badge. Lichess shows that a free, open chess site can run on patrons. Sarce's
  community is smaller, so treat this as a supplement.
- **Self-host support:** a paid setup or support plan for clubs and schools that want their own instance.
- **Creator partnerships:** style cards and "play like Tal" weekly challenges with chess streamers. Revenue
  share on Plus sign-ups through their link.
- **Not recommended:** ads (they break the coaching tone), selling or sharing data (it breaks trust and
  privacy law), and paywalling Brilliant % (it breaks principle 1).

## Unit economics to check

Using the cost model in [COMPUTE.md](./COMPUTE.md):

```text
Margin per Plus player = price − (cloud CPU-hours × price per CPU-hour) − storage − payment fees − store cut
```

With the example assumptions there (a regular bullet player at about 13.5 CPU-hours a month), cloud
compute is under $1 a month on dedicated servers. So a $4 plan has room, *if* Part C of the benchmark
confirms the CPU per game. The one-off backfill (~135 CPU-hours for 3,000 games) is the expensive part:
spread it over the first weeks of a subscription, or run it on the player's Node.

## Order

1. Deploy a hosted beta (free), run the pilot, and ask what players would pay for (BENCHMARK Part D).
2. Before taking any money:
   - CLA and trademark ([LEGAL.md](./LEGAL.md));
   - an answer from Chess.com legal;
   - the privacy notice and PDPC registration.
3. Launch Supporters first (no promises to keep), then Plus, then Coach.
