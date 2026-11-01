# Style pilot deployment

The admitted pilot is one persistent API/worker in Singapore, Supabase Auth and PostgreSQL in Singapore, and the web app on Vercel. The release owner must record exact deployed revisions in the release evidence; this document does not make a deployment claim.

## Capacity and isolation

- Start with 4 vCPU and 16 GB RAM. Run one Uvicorn worker because the durable database queue provides concurrency and prevents in-memory duplicate scheduling.
- Set `ANALYSIS_WORKERS=2` initially. Increase only after observing memory, queue age and analysis latency during a dry run.
- Bind the API only to loopback behind TLS termination. Store the Supabase service-role key in the host secret store, never in the image, repository, Vercel or a `NEXT_PUBLIC_*` variable.
- Pin the approved official Stockfish archive URL and SHA-256 at build time. Keep Maia-2 forced with `HUMAN_MODEL=maia2`; the pilot must not silently fall back to the heuristic.

## Bring-up

1. Provision an Ubuntu 24.04 SGP1 VM with 4 vCPU, 16 GB RAM and at least 80 GB disk. Run `sudo deploy/pilot/bootstrap-ubuntu.sh <operator-ip/cidr>`; never leave SSH open to the world.
2. Create the Singapore Supabase project, apply every migration in order, configure allowed Auth redirects, and retain the migration log.
3. Populate `/etc/sarce/pilot.env` as root and keep mode `0600`. Put the candidate SHA, immutable image digest, Supabase service role, operator IDs and 30-day retention there. Never copy this file into an image or Vercel.
4. Build `deploy/pilot/docker-compose.build.yml` from the exact candidate SHA, push it, resolve its registry digest, then deploy `deploy/pilot/docker-compose.yml` using `PILOT_IMAGE_REF=repository@sha256:digest`. Do not deploy a mutable tag.
5. Install `deploy/pilot/Caddyfile` and `caddy.service.override.conf`, supply `PILOT_API_DOMAIN` and `ACME_EMAIL` through Caddy's root-owned environment, run `systemctl daemon-reload`, validate with `caddy validate`, and reload Caddy. The API remains bound only to `127.0.0.1:8000`.
6. Configure Vercel `NEXT_PUBLIC_API_URL` to that HTTPS origin and deploy the exact candidate Git SHA.
7. Require `GET /health/ready` to return 200. A 503 is a release blocker even when `/health` is live.
8. Run `npm run pilot:smoke -- --output <file>` and verify the disposable job survives an API restart without duplicate results.

## Backup and restore gate

Enable managed daily database backups with 30-day retention before invitations are issued. Export the deletion ledger outside the database, restore into an isolated Singapore project, compare owner-table counts, then apply the ledger before that environment can become ready:

```powershell
python -m scripts.restore_deletion_check --export <external-ledger.json>
python -m scripts.restore_deletion_check --apply <external-ledger.json> --result <restore-check.json> `
  --artifact-sha <candidate-sha> --image-digest <sha256:digest> `
  --backup-id <provider-backup-id> --restore-project-id <isolated-project-id> `
  --source-counts <source-owner-counts.json> --restored-counts <restored-owner-counts.json> `
  --verified-by <operator-id>
```

Require zero remaining deleted-owner rows. Record the source/restored owner-table comparison, backup identifier, restore time, verifier and discrepancies in release evidence. Never restore a backup into the live project as a test.

## Monitoring and rollback

Run `npm run pilot:ops-check -- --output <file>` from the VM on schedule. Alert on readiness failures, oldest queue age, failed jobs, monitor alerts, disk below 15%, memory above 90%, or any recent 5xx response. Stop new invitations when durable writes, tenant isolation, consent, export, deletion or analysis correctness are uncertain. Roll back the web and API to their recorded immutable revisions; do not roll back migrations. Apply a forward migration if schema repair is required.
