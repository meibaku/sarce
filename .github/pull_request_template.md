## Summary

<!-- What changed and why — tie back to docs/PHILOSOPHY.md if relevant -->

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
- [ ] `npm run test:golden` (if classification thresholds changed + Stockfish available)

## Docs

- [ ] Updated `docs/PHASES.md` status if completing a stage
- [ ] Updated `docs/ARCHITECTURE.md` if structure changed
