# Sarce Architecture

## Local-first principle

Sarce is designed to run **entirely on your machine** during development. No cloud
services are required until you choose to deploy.

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR MACHINE (local)                      │
│                                                                  │
│  ┌──────────────┐    proxy      ┌──────────────┐                │
│  │  Next.js     │ ────────────► │  FastAPI     │                │
│  │  :3000       │  /api/backend │  :8000       │                │
│  │  apps/web    │               │  apps/api    │                │
│  └──────────────┘               └──────┬───────┘                │
│                                        │                         │
│                         ┌──────────────┼──────────────┐         │
│                         ▼              ▼              ▼         │
│                  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│                  │ Stockfish│  │ Chess.com│  │ Supabase     │  │
│                  │ (local   │  │ public   │  │ local :54321 │  │
│                  │  binary) │  │ API      │  │ Postgres     │  │
│                  └──────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Why local-first?

| Concern | Local approach |
|---------|----------------|
| Stockfish | Runs on your CPU — no cloud engine fees |
| Game data | Postgres via `supabase start` on localhost |
| Auth | Supabase local auth; optional `LOCAL_USER_ID` bypass for API-only dev |
| Chess.com | Public API — no keys, works offline for cached games |
| Analysis | In-process FastAPI `BackgroundTasks` (no Redis/queue needed locally) |

### Production path (later)

Same architecture scales by:

1. Deploying `apps/api` to a container (Fly.io, Railway, etc.) with Stockfish installed
2. Pointing env vars at hosted Supabase instead of `supabase start`
3. Replacing `BackgroundTasks` with a job queue (Celery, Supabase Edge Functions + pg_cron)
4. Adding `apps/mobile` (Expo) as another client to the same API

---

## Monorepo layout

```
sarce/
├── apps/
│   ├── web/                 # Next.js dashboard (Phase 1)
│   └── api/                 # FastAPI analysis engine (Phase 1)
│       ├── app/
│       │   ├── routers/     # HTTP endpoints
│       │   ├── services/    # Business logic
│       │   └── db/          # Supabase client
│       ├── scripts/         # One-off batch jobs (Tal benchmark)
│       └── tests/           # pytest suite
├── supabase/
│   ├── migrations/          # Schema (versioned)
│   ├── seed.sql             # Local dev user + Tal seed
│   └── config.toml
└── docs/
    ├── ARCHITECTURE.md      # This file
    └── PHASES.md            # Phase 1–3 roadmap + status
```

---

## Data flow (Phase 1)

```
1. IMPORT
   User enters Chess.com username
   → POST /games/import
   → ChessComClient fetches archives
   → PGN parsed, stored in `games` (status: pending)

2. ANALYZE (background)
   → AnalysisService picks pending games
   → StockfishEngine classifies each USER move at depth 18
   → Brilliant detector runs on non-best moves
   → Results → `game_moves` + `game_analyses`
   → Status → complete

3. BASELINE
   → BaselineService aggregates all `game_analyses` for user/username
   → Upserts `user_baselines` (Brilliant %, full distribution)

4. DISPLAY
   → Dashboard fetches baseline, timeline, Tal reference via API
   → Gauge, distribution bars, line chart
```

---

## Style vector schema (versioned)

Stored in `style_vectors.vector` and `game_analyses.style_vector`:

```json
{
  "version": 1,
  "brilliantPct": 8.2,
  "sacrificeRate": 0.12,
  "tacticalComplexity": 0.0,
  "evalVolatility": 0.45,
  "distribution": {
    "best": 40, "excellent": 20, "good": 15,
    "inaccuracy": 10, "mistake": 5, "blunder": 2,
    "miss": 3, "brilliant": 8
  }
}
```

`version` increments when features change (Phase 2 adds similarity vectors).

---

## Key services

| Service | Responsibility |
|---------|----------------|
| `ChessComClient` | Fetch archives + game JSON from Chess.com |
| `GameStore` | Persist imported PGNs |
| `StockfishEngine` | UCI engine wrapper (reused per game) |
| `MoveClassifier` | Centipawn loss → quality tiers + brilliant |
| `AnalysisService` | Orchestrate classify → persist → baseline |
| `BaselineService` | Aggregate distributions, compute Brilliant % |
| `ReferenceService` | Tal PGN batch job + benchmark cache |

---

## Environment variables

See `.env.example`. Critical for local dev:

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | `http://127.0.0.1:54321` when using `supabase start` |
| `SUPABASE_SERVICE_ROLE_KEY` | From `supabase status` — API writes bypass RLS |
| `STOCKFISH_PATH` | Folder or path to `stockfish*.exe` |
| `LOCAL_USER_ID` | Fixed UUID for local dev without login |
| `ANALYSIS_DEPTH` | Stockfish depth (default 18) |

---

## Security notes

- **Service role key** stays server-side only (FastAPI `.env`, never `NEXT_PUBLIC_`)
- RLS enabled on all tables; frontend reads via API, not direct DB for Phase 1
- `user_metadata` never used for authorization (Supabase best practice)
