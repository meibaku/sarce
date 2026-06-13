# Contributing to Sarce

Read **[docs/PHILOSOPHY.md](docs/PHILOSOPHY.md)** first — it's the product constitution.

## Before you code

1. Which **phase/stage** does this belong to? → [docs/PHASES.md](docs/PHASES.md)
2. Does it align with **style over accuracy**? → [docs/adr/0001-style-over-accuracy.md](docs/adr/0001-style-over-accuracy.md)
3. If not, write an ADR (`docs/adr/0000-template.md`)

## Quality gates

| Command | What it checks |
|---------|----------------|
| `npm run ci` | Full local gate (API tests + web lint + build) |
| `npm run test:api` | Unit + architecture + philosophy contracts |
| `npm run test:golden` | Stockfish regression (local, needs engine) |
| `npm run lint:web` | Next.js ESLint |
| `npm run build:web` | TypeScript production build |

CI runs on every PR: `.github/workflows/ci.yml`

## Adding features

### Must preserve

- **Brilliant** as first-class tier
- **Brilliant %** as headline metric (6–10% default target)
- **Style vector versioning**
- Engine as mirror, not judge (no "accuracy score" replacing style)

### Must avoid (without ADR)

- ML classification in Phase 1
- Punitive copy ("blunder rate" as shame metric)
- Competitive leaderboards
- Removing Brilliant tier or merging it into Best

## Architecture rules

- `routers/` — HTTP only, no Stockfish
- `services/` — all business logic
- `tests/test_architecture.py` — enforces boundaries
- `tests/test_philosophy_contracts.py` — enforces product invariants

## ADRs

Architecture Decision Records live in `docs/adr/`. Required when changing what "style" means.
