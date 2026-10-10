## Summary

<!-- What changed and why — tie back to docs/PHILOSOPHY.md if relevant -->

## Base branch

**Target: `staging`** — feature/fix/chore PRs merge here first. Use the [promotion template](https://github.com/meibaku/sarce/blob/staging/.github/PULL_REQUEST_TEMPLATE/promotion.md) for `staging` → `main`.

## Philosophy check

_Sarce tracks style identity, not engine accuracy. Brilliant % is the headline metric._

- [ ] Does **not** frame sacrificial/style play as failure
- [ ] **Brilliant %** remains headline metric (if UI/API metrics touched)
- [ ] Copy is encouraging, not punitive ("distance from goal" not "you failed")
- [ ] Reference players used as **benchmarks**, not leaderboards
- [ ] `style_vector.version` bumped if style schema changed
- [ ] ADR added if this contradicts [docs/PHILOSOPHY.md](../docs/PHILOSOPHY.md)

## Test plan

- [ ] `npm run ci` passes locally
- [ ] `npm run ci:security` passes locally
- [ ] `npm run test:golden` (if classification thresholds changed + Stockfish available)

## Safety

- [ ] No secrets, service-role keys, or `.env` files in the diff
- [ ] New tables enable RLS; schema changes are a new migration (old ones untouched)

## Greptile / AI review

- [ ] Greptile foundation comments (Brilliant tier, headline metric, ML, client Stockfish) dismissed only with ADR or fix
- [ ] See [docs/CODE_REVIEW.md](../docs/CODE_REVIEW.md) for false positives vs real issues

## Docs

- [ ] Updated `docs/PHASES.md` status if completing a stage
- [ ] Updated `docs/ARCHITECTURE.md` if structure changed
