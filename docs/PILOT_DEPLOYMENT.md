# Style pilot deployment

The admitted pilot is one persistent API/worker in Singapore, Supabase Auth and PostgreSQL in Singapore, and the web app on Vercel. The release owner must record exact deployed revisions in the release evidence; this document does not make a deployment claim.

## Capacity and isolation

- Start with 4 vCPU and 16 GB RAM. Run one Uvicorn worker because the durable database queue provides concurrency and prevents in-memory duplicate scheduling.
- Set `ANALYSIS_WORKERS=2` initially. Increase only after observing memory, queue age and analysis latency during a dry run.
- Bind the API only to loopback behind TLS termination. Store the Supabase service-role key in the host secret store, never in the image, repository, Vercel or a `NEXT_PUBLIC_*` variable.
- Pin the approved official Stockfish archive URL and SHA-256 at build time. Keep Maia-2 forced with `HUMAN_MODEL=maia2`; the pilot must not silently fall back to the heuristic.

## Bring-up

1. Create the Singapore Supabase project, apply every migration in order, configure allowed Auth redirects, and retain the migration log.
2. Copy `deploy/pilot/.env.example` to an operator-only secret file and replace every placeholder.
3. Build with the reviewed Stockfish artifact, then start `deploy/pilot/docker-compose.yml` on the persistent host.
4. Configure the reverse proxy so only HTTPS reaches the API. Configure Vercel `NEXT_PUBLIC_API_URL` to that origin and deploy the exact reviewed web SHA.
5. Require `GET /health/ready` to return 200. A 503 is a release blocker even when `/health` is live.
6. Redeem a disposable invitation and complete one finished-game analysis. Verify the job survives an API restart and the result is visible only to its owner.

## Backup and restore gate

Enable managed daily database backups before invitations are issued. Perform a restore into an isolated project, verify row counts for profiles, games, analyses, pilot consent and feedback, and then destroy the restore project. Record backup identifier, restore time, verifier and discrepancies in the release evidence. Never restore a backup into the live project as a test.

## Monitoring and rollback

Alert on readiness failures, queue age, failed jobs, disk pressure, memory pressure and 5xx rate. Stop new invitations when durable writes, tenant isolation, consent, export, deletion or analysis correctness are uncertain. Roll back the web and API to their recorded revisions; do not roll back migrations. Apply a forward migration if schema repair is required.
