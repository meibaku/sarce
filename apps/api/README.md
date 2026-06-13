# Sarce API

FastAPI backend for chess style analysis. See `docs/ARCHITECTURE.md` for local-first setup.

## Quick start (local)

```powershell
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# From repo root — start Supabase local first
# supabase start
# Copy keys from: supabase status

uvicorn app.main:app --reload --port 8000
```

## Run tests

```powershell
pytest -v
# or from repo root:
npm run test:api
```

Unit tests cover classification, brilliant detection, baseline math, PGN parsing, and health endpoint.
Integration tests requiring Supabase + Stockfish are run manually.

## Key endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/games/import` | Import Chess.com games + analyze |
| GET | `/games` | List games |
| POST | `/games/analyze` | Analyze pending games |
| GET | `/analysis/baseline/{user_id}` | User baseline |
| GET | `/analysis/timeline/{user_id}` | Brilliant % over time |
| GET | `/reference/tal` | Tal benchmark |
| POST | `/reference/tal/process` | Run Tal batch job |

## Tal benchmark

```powershell
python -m scripts.process_tal_benchmark --max-games 5
```

## Services

- `services/chess_com.py` — Chess.com public API client
- `services/move_classifier.py` — Stockfish → quality tiers
- `services/brilliant.py` — Tal-style brilliant detection
- `services/analysis.py` — Full analysis pipeline
- `services/baseline.py` — Rolling aggregation
- `services/reference.py` — Tal PGN benchmark
