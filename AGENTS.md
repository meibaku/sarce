# Sarce monorepo — agent instructions

Chess **style identity** app (Tal-inspired, 6–10% Brilliant target) — not an engine accuracy coach.
Package manager: **npm** (workspaces) for `apps/web`, standalone npm for `apps/mobile`; **pip** for `apps/api`.

## Read first

| Doc | Why |
| --- | --- |
| [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) | Product constitution — CI-enforced |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Local-first layout, where code goes |
| [`docs/CHAOS_PLAN.md`](docs/CHAOS_PLAN.md) | Current milestone plan and its ground rules |
| [`docs/QUALITY_GATES.md`](docs/QUALITY_GATES.md) | CI jobs, rulesets, Greptile |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Branching, commits, conventions |

## Workspace map

| Path | Role |
| --- | --- |
| `apps/web` | Next.js UI only — talks to the API through `src/lib/api.ts` |
| `apps/mobile` | Expo (React Native) app — same API, own lockfile; see `apps/mobile/AGENTS.md` |
| `apps/api` | FastAPI — Stockfish, classification and all business logic in `app/services/` |
| `supabase/migrations` | Schema + RLS; append-only |
| `docs/` | Philosophy, spec, ADRs (`docs/adr/`) |
| `scripts/` | CI and PR helpers (Node, dependency-free) |

## Domain invariants

Changing any of these needs an ADR in `docs/adr/` first:

- **Brilliant** stays a first-class move tier, and **Brilliant %** stays the headline metric.
- Engine is a mirror, not a judge — no punitive user-facing copy (`philosophy-check` guards this).
- Stockfish runs **server-side only** (`apps/api`); routers never import `chess` / `chess.engine`.
- `apps/web` never uses the Supabase service-role key; nothing secret goes in `NEXT_PUBLIC_*`.
- New tables enable RLS. Schema changes are a **new** migration — never edit an old one.
- Bump `style_vectors.version` when the style schema's meaning changes.
- **Post-game only** — never analyze an unfinished game (Chess.com / Lichess fair-play rules).
- Ask before adding a heavy dependency (torch, onnxruntime, celery, redis, …).

## Workflow

```text
feat/* | fix/* | chore/*  →  staging  →  main
```

- Branch from `origin/staging`; one milestone or concern per PR, aimed at roughly 800 changed lines or fewer so it stays reviewable.
- Conventional commit prefixes: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- Update `CHANGELOG.md`; tick stages in `docs/PHASES.md` / `docs/CHAOS_PLAN.md` when one completes.
- Never push to `staging` or `main` directly — open a PR (`npm run pr:create -- --title "..."`).

## Documentation comments on touched files

Add short docstrings/comments where they help maintenance: intent, invariants, safety boundaries,
fallbacks, non-obvious control flow. Match the density of the surrounding file; do not restate code.

## Local commands

```bash
npm ci
npm run ci            # secret scan + api tests + web lint + web build
npm run ci:security   # secret scan + npm audit (critical)
npm run test:arch     # architecture + philosophy contracts
npm run test:golden   # Stockfish regression (needs a local engine)
```
