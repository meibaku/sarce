# Sarce — Greptile foundation rules

**Read before suggesting changes.** Sarce is a style-identity app, not an accuracy coach.

## Immutable product foundations (DO NOT suggest changing)

These require an ADR in `docs/adr/` before any code change:

1. **Brilliant is a first-class move tier** — never merge into Best, remove, or deprecate
2. **Brilliant % is the headline dashboard metric** — never replace with accuracy, centipawn loss, or "engine match %"
3. **Engine is mirror, not judge** — Stockfish informs eval; user's style goal defines success
4. **Style over accuracy** — see `docs/adr/0001-style-over-accuracy.md`
5. **Phase 1 is rule-based only** — no ML/sklearn/torch for classification without ADR
6. **Stockfish runs server-side only** — never move analysis to Next.js client or mobile
7. **Personal, not competitive** — no public leaderboards, shame metrics, or punitive copy

## Comments to AVOID posting (false positives)

Do **not** flag these as bugs or required fixes:

- Heuristic brilliant detection in `brilliant.py` — approximate by design; tunable via `.env`
- `MISS` detection thresholds in `move_classifier.py` — Phase 1 heuristic
- Classifying **user moves only** (not all plies) — intentional
- `BackgroundTasks` for analysis instead of Redis/Celery — Phase 1 local-first choice
- Low brilliant % framed as user failure in copy — CI already guards; don't suggest punitive UX
- Suggesting "use ML for better classification" — out of scope unless ADR exists

## DO flag (high value reviews)

### Security
- `SUPABASE_SERVICE_ROLE_KEY` or secrets in `NEXT_PUBLIC_*` or client bundles
- New tables without RLS in `supabase/migrations/`
- `user_metadata` used in RLS or authorization
- User-controlled strings passed to Stockfish path or shell
- Missing input validation on API endpoints

### Architecture
- Stockfish/chess.engine imports in `apps/api/app/routers/`
- Business logic added to routers instead of `services/`
- Direct Supabase service-role usage from `apps/web` (must go through API)
- Breaking API response shape for `brilliantPct`, baseline, timeline without migration plan

### Philosophy / UX
- User-facing copy that shames style play ("you failed", "terrible", "stop sacrificing")
- Default sort/filter that emphasizes blunders over Brilliant progress
- Removing `BrilliantGauge`, `brilliantPct`, or timeline chart from dashboard

### Database
- `style_vectors` changes without bumping `version`
- Dropping `brilliant` from quality CHECK constraints
- Views without `security_invoker` on Postgres 15+

## Monorepo layout (preserve)

```
apps/web/     → Next.js UI only; calls API via src/lib/api.ts
apps/api/     → FastAPI; all Stockfish + classification in services/
supabase/     → migrations with RLS
docs/         → PHILOSOPHY.md is law; PRODUCT_SPEC.md is scope
```

## Phase scope

Only suggest features matching current phase in `docs/PRODUCT_SPEC.md`. Defer to Phase 4+ backlog:
video/transcript (Phase 2), intent journal (Phase 3), Lichess, Redis queues, microservices.

## When suggesting refactors

- Prefer minimal diffs — match existing patterns in the file
- Do not rename `brilliant` → `excellent` or similar across the codebase
- Do not add dependencies without justification
- Match docstring level of surrounding code
