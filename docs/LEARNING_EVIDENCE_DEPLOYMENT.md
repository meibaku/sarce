# Learning Evidence staging deployment

This runbook creates a dedicated, invite-only staging environment. It does not deploy from an unreviewed branch and
does not turn a green build into a learning claim. The readiness artifact remains blocked until every named gate has
current evidence.

## Topology

Create three isolated staging resources:

1. A Supabase project for Auth and Postgres. Apply every migration in order; never point staging at production data.
2. A Vercel FastAPI project with Root Directory `apps/api`. Vercel detects `app/main.py`; `vercel.json` caps bounded
   requests at 30 seconds.
3. A Vercel Next.js project with Root Directory `apps/web`, proxying `/api/backend/*` to the staging API.

The Vercel API is deliberately request-only. Stockfish, the analysis monitor, automatic sync, queue workers, orphan
sweeps, node finishing and FastAPI `BackgroundTasks` routes are refused. Run analysis and item-bank preparation on a
persistent paired Sarce Node or another host using the server's token-protected node gateway.

## API environment

Set these as protected staging variables; never commit their values:

```text
SUPABASE_URL=https://<staging-project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only>
AUTH_REQUIRED=true
REQUEST_ONLY_RUNTIME=true
JOB_QUEUE_ENABLED=false
AUTO_SYNC_ENABLED=false
NODE_TOKEN=
LEARNING_OPERATORS=["<verified-user-uuid>"]
LEARNING_REVIEWERS=["<verified-reviewer-uuid>"]
CORS_ORIGINS=["https://<staging-web-host>"]
```

`STOCKFISH_PATH` is intentionally absent from this project. A request-only deployment must return HTTP 503 for
`/play`, `/monitor`, import/analyse, engine-backed drill/scouting, sync, rebuild and Tal-processing routes.

## Web and native environment

The web Vercel project needs `API_URL`, `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`. The Expo
development/staging build needs `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_WEB_URL`, `EXPO_PUBLIC_SUPABASE_URL` and
`EXPO_PUBLIC_SUPABASE_ANON_KEY`. Supabase Auth must allow both the web callback and the `sarce://learning` native
callback. Test native email links in a development build; Expo Go does not provide a stable authentication callback.

## Admission smoke

After the reviewed stack reaches `staging`:

1. Confirm `/health` is 200 and an engine/background route is 503.
2. Sign in as the configured operator and create an even invitation batch.
3. Redeem one token with a separate verified adult test account; confirm the token cannot be reused.
4. Confirm `/learning/status` and pre-answer presentation payloads contain neither arm, participant key, answer,
   concept/family metadata nor another reviewer vote.
5. Record a test response, then verify feedback appears only after the append-only attempt exists.
6. Withdraw the test account and confirm no new session can be created.

Record the staging URLs, migration state, CI run, Greptile result, bank qualification and smoke evidence in
`docs/evidence/le2-pilot-readiness.json`. Only change its decision to `ready` when every gate is supported.
