# Sarce

[![CI](https://github.com/meibaku/sarce/actions/workflows/ci.yml/badge.svg)](https://github.com/meibaku/sarce/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)

Personal chess companion focused on **style analysis** — not "what was the best move," but "did this game feel like *you*?"

Track progress toward a Tal-inspired playing identity: **6–10% Brilliant** sacrificial moves, game by game. The engine is a mirror for self-development, not a judge.

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md) | **Master spec** — full vision & build roadmap |
| [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md) | Product constitution |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Local-first system design |
| [docs/PHASES.md](docs/PHASES.md) | Roadmap (Phase 1–3) |
| [docs/QUALITY_GATES.md](docs/QUALITY_GATES.md) | CI, tests, rulesets |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [SECURITY.md](SECURITY.md) | Report vulnerabilities |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

## Architecture (local-first)

```
Next.js :3000  →  FastAPI :8000  →  Stockfish (local) + Supabase local :54321
```

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the full diagram.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js (React, TypeScript) |
| Mobile (future) | Expo / React Native |
| Backend | Python (FastAPI) + `python-chess` |
| Engine | Stockfish (server-side, local binary) |
| Database & Auth | Supabase (Postgres) |
| Game source | Chess.com public API |

## Monorepo layout

```
sarce/
├── apps/
│   ├── web/          # Next.js dashboard
│   └── api/          # FastAPI — import, analysis, classification
├── docs/             # Architecture, philosophy, ADRs
├── supabase/         # Migrations, seed, local config
└── package.json
```

## Quick start (local)

### Prerequisites

- Node.js 20+ (the version CI runs)
- Python 3.11+
- [Supabase CLI](https://supabase.com/docs/guides/cli) + Docker Desktop
- Stockfish binary in `STOCKFISH_PATH` (see `.env.example`)

### Setup

```powershell
# Supabase
supabase start
supabase db reset
supabase status          # copy keys → .env

# Environment
cp .env.example .env

# Backend
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
npm install
npm run dev:web
```

Open [http://localhost:3000](http://localhost:3000) — enter your Chess.com username.

### Tests

```powershell
npm run ci              # full gate
npm run test:golden     # Stockfish regression (local)
```

## Phase status

| Phase | Status |
|-------|--------|
| **1** — Import, classify, Brilliant %, Tal benchmark | ✅ Complete |
| **2** — Video position capture + transcript context | ✅ Complete |
| **3** — Move intent journal + style goals | ✅ Complete |
| **Chaos plan** M0–M8 — style lenses, validation, trap atlas, sharing | ✅ Merged ([docs/CHAOS_PLAN.md](docs/CHAOS_PLAN.md)) |

What's next: [docs/REVIEW_2026-10.md](docs/REVIEW_2026-10.md) (trajectory and maths review) and
[docs/BENCHMARK.md](docs/BENCHMARK.md) (Lichess and Chess.com comparison).

## Contributing

Contributions welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md) first. All changes go through PR + CI.

## Security

Report vulnerabilities privately via [GitHub Security Advisories](https://github.com/meibaku/sarce/security/advisories/new). See [SECURITY.md](SECURITY.md).

## License

[GNU Affero General Public License v3.0](LICENSE) — Copyright (c) 2026 meibaku.

You can use, self-host and modify Sarce freely. If you run a modified version for other people over a
network, you must offer them its source under the same licence (AGPL section 13). See ADR 0006.
