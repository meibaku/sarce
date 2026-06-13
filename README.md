# Sarce

Personal chess companion focused on **style analysis** — not "what was the best move," but "did this game match my preferred style?"

## Architecture (local-first)

Everything runs on your machine during development. See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the full diagram and **[docs/PHASES.md](docs/PHASES.md)** for phase roadmap.

```
Next.js :3000  →  FastAPI :8000  →  Stockfish (local) + Supabase local :54321
```

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js (React, TypeScript) |
| Mobile (future) | Expo / React Native |
| Backend | Python (FastAPI) + `python-chess` |
| Engine | Stockfish (server-side, local binary) |
| Database & Auth | Supabase (Postgres) — `supabase start` for local |
| Game source | Chess.com public API |

## Monorepo layout

```
sarce/
├── apps/
│   ├── web/          # Next.js dashboard
│   └── api/          # FastAPI — import, analysis, classification
├── docs/             # Architecture + phase docs
├── supabase/         # Migrations, seed, local config
└── package.json
```

## Quick start (local)

### 1. Prerequisites

- Node.js 18+
- Python 3.11+
- [Supabase CLI](https://supabase.com/docs/guides/cli)
- Stockfish binary in `STOCKFISH_PATH` (see `.env.example`)

### 2. Supabase local

```powershell
supabase start
supabase db reset    # applies migrations + seed.sql (local user)
supabase status      # copy URL + keys to .env
```

### 3. Environment

```powershell
cp .env.example .env
# Fill in keys from `supabase status`
```

### 4. Backend

```powershell
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5. Frontend

```powershell
npm install
npm run dev:web
```

Open [http://localhost:3000](http://localhost:3000). Enter your Chess.com username to import and analyze.

### 6. Tests

```powershell
npm run test:api
```

### 7. Tal benchmark (optional)

```powershell
cd apps/api
python -m scripts.process_tal_benchmark --max-games 5
```

## Phase 1 — Complete

- ✅ Chess.com import + PGN storage
- ✅ Stockfish classification (depth 18, user moves only)
- ✅ Brilliant detection (Tal-style rules)
- ✅ Baseline aggregation + dashboard with live data
- ✅ Brilliant % timeline chart
- ✅ Tal reference benchmark pipeline
- ✅ pytest suite

## Phase 2 — Next

Reference player comparison by Chess.com username. Schema ready.

## Phase 3 — Later

Per-move highlights, adjustable style goals, community groupings.

## License

Private — meibaku/sarce
