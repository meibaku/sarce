# Contributing to Sarce

Thank you for helping build a chess companion focused on **style identity**, not engine accuracy.

**Read first:** [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md) — the product constitution.

## Quick links

| Doc | When to read |
|-----|--------------|
| [PHILOSOPHY.md](docs/PHILOSOPHY.md) | Always — before any feature or copy change |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Structural or infrastructure changes |
| [QUALITY_GATES.md](docs/QUALITY_GATES.md) | CI, tests, branch rules |
| [CODE_REVIEW.md](docs/CODE_REVIEW.md) | Human + Greptile review guide |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community interaction |
| [SECURITY.md](SECURITY.md) | Security issues |

## Development workflow

```text
feat/* | fix/* | chore/*  →  staging  →  main
```

| Branch | Role |
|--------|------|
| `feat/*`, `fix/*`, `chore/*` | Short-lived work branches, one concern each |
| `staging` | Integration — **default branch and default PR target** |
| `main` | Released code only; promoted from `staging` |

Both `staging` and `main` are protected by GitHub **rulesets** — all changes require a PR that passes CI.
Promote with the [promotion template](.github/PULL_REQUEST_TEMPLATE/promotion.md) (`npm run pr:promote`).
Hotfix: branch from `main`, PR to `main`, then back-merge into `staging`.

Keep PRs reviewable: aim for roughly **800 changed lines or fewer** (lockfiles excluded) and split larger work.

```powershell
# 1. Fork & clone (or work on a branch if you have write access)
git fetch origin
git checkout -b feat/your-feature origin/staging

# 2. Set up locally — see README.md Quick start

# 3. Make changes, run gates locally
npm run ci

# 4. Commit (clear message, reference phase if relevant)
git commit -m "feat: add reference player picker (Phase 2)"

# 5. Push and open PR into staging — template will guide philosophy check
git push -u origin feat/your-feature
npm run pr:create -- --title "feat: add reference player picker (Phase 2)"
```

### Required CI checks (PR must pass)

- `api-test` — pytest (unit + architecture + philosophy)
- `web-lint` — ESLint
- `web-build` — Next.js production build
- `migration-check` — Supabase migration sanity
- `philosophy-check` — no punitive copy; Brilliant gauge present
- `security-gates` — secret scan (`scripts/ci/secret-scan.mjs`) + `npm audit --audit-level=critical`

### Secrets

Never commit `.env*`, signing keys, or the Supabase service-role key. Run `npm run ci:security` before pushing.

## Before you code

1. Which **phase/stage**? → [docs/PHASES.md](docs/PHASES.md)
2. Aligns with **style over accuracy**? → [docs/adr/0001-style-over-accuracy.md](docs/adr/0001-style-over-accuracy.md)
3. If not → write an ADR ([template](docs/adr/0000-template.md))

## Code conventions

### Python (`apps/api`)

- Business logic in `app/services/` — routers stay thin
- Docstrings on services explaining phase and philosophy alignment
- Tests in `apps/api/tests/` — add philosophy/architecture tests for invariant changes
- No ML frameworks in Phase 1 without ADR

### TypeScript (`apps/web`)

- Components in `src/components/`, types in `src/types/`
- API calls via `src/lib/api.ts`
- User-facing copy: encouraging, never punitive (see PHILOSOPHY.md)

### Database

- Migrations in `supabase/migrations/` — enable RLS on new tables
- Bump `style_vector.version` if style schema changes

## What to preserve

- **Brilliant** as first-class move tier
- **Brilliant %** as headline metric (6–10% default target)
- **Style vector versioning**
- Engine as mirror, not judge

## What to avoid (without ADR)

- ML classification in Phase 1
- Punitive copy ("blunder rate" as shame metric)
- Competitive leaderboards
- Merging Brilliant into Best

## AI code review (Greptile)

Sarce uses [Greptile](https://www.greptile.com/) with `.greptile/` configs that **lock product foundations** — Brilliant tier, Brilliant % headline, server-side Stockfish, no ML in Phase 1.

- Read [docs/CODE_REVIEW.md](docs/CODE_REVIEW.md) before arguing with Greptile comments
- Do not disable foundation rule IDs in root `.greptile/config.json`
- Foundation change suggestions require an ADR, not a drive-by refactor

Maintainers: install the Greptile GitHub App on the repo to enable reviews.

## Commits & PRs

- Use clear, complete sentences in commit messages
- PR title: `feat:`, `fix:`, `docs:`, `test:`, `chore:` prefix when helpful
- Fill out the PR template philosophy checklist
- Link related issues if any

## License

By contributing, you agree your contributions are licensed under the [MIT License](LICENSE).

## Questions

Open a [feature request](.github/ISSUE_TEMPLATE/feature_request.yml) or [bug report](.github/ISSUE_TEMPLATE/bug_report.yml) — both include philosophy alignment prompts.
