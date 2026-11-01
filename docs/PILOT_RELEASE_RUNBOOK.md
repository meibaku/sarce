# Style pilot release runbook

The repository contains a functioning pilot path, but code completion is not pilot admission. Keep `docs/evidence/style-pilot-readiness.json` blocked until each statement is backed by current evidence for the exact artifact SHA.

## Before admission

1. Obtain named legal/product-owner approval for the adult consent text, privacy notice, retention and deletion behavior.
2. Require green CI, architecture/philosophy contracts, API tests, web lint/build and the Stockfish golden regression on the artifact SHA.
3. Apply migrations to the Singapore production project and retain the ordered migration output.
4. Verify two-user isolation across games, analyses, notes, consent, feedback, exports and operator endpoints.
5. Complete the restart, backup/restore, export/deletion, and 390 px plus desktop browser smoke tests from `PILOT_DEPLOYMENT.md`.
6. Record immutable deployment URL, API image digest, database region, evidence identifiers, verifier and UTC timestamp.
7. Change each gate to `true` and status to `admitted` only after the linked evidence exists. Run `npm run pilot:admit -- <full-artifact-sha>`; invitation creation remains prohibited if it fails.

## Restore deletion check

Completed deletion jobs are durable tombstones. Export their ledger before a restore, then reapply it to the restored database before that environment can report ready:

```powershell
cd apps/api
python -m scripts.restore_deletion_check --export <durable-ledger.json>
python -m scripts.restore_deletion_check --apply <durable-ledger.json> --result <restore-check.json>
```

Store the ledger outside the restored database. Configure `PILOT_RESTORE_CHECK_PATH` with the passing result and `PILOT_BACKUP_RETENTION_DAYS` with the approved retention period. Readiness must fail when either value is absent or invalid. Attach the result, retention period, restored project and rehearsal identifiers to the exact runtime SHA's release evidence.

## Two-user production rehearsal

Run this only against the isolated pilot deployment. It creates two confirmed disposable users, imports one finished public Chess.com game, clones that owned row into disposable reads for the first-ten boundary, exercises account deletion, and removes the disposable identities after writing evidence.

Provide secrets only through the process environment. `PILOT_OPERATOR_ACCESS_TOKEN` must belong to an already configured pilot operator; the output never contains tokens, emails, raw user identifiers, or exception messages.

```powershell
$env:PILOT_API_URL = "https://api.pilot.example"
$env:PILOT_ARTIFACT_SHA = "<40-character-candidate-sha>"
$env:PILOT_IMAGE_DIGEST = "sha256:<deployed-image-digest>"
$env:PILOT_SMOKE_CHESSCOM_USERNAME = "<account-with-a-finished-public-game>"
$env:PILOT_RESTART_COMMAND = "docker compose -f /opt/sarce/docker-compose.yml restart api"
$env:SUPABASE_URL = "https://<project>.supabase.co"
$env:SUPABASE_ANON_KEY = "<runtime-secret>"
$env:SUPABASE_SERVICE_ROLE_KEY = "<runtime-secret>"
$env:PILOT_OPERATOR_ACCESS_TOKEN = "<runtime-secret>"
npm run pilot:smoke -- --output docs/evidence/pilot-smoke.json
```

The command fails unless all named checks pass. Treat a failed or partial JSON result as diagnostic evidence only. Confirm the evidence SHA and digest match the deployed candidate before attaching it to readiness. Cleanup occurs after the JSON file is durably written; investigate and remove any remaining `pilot-smoke-*` accounts if the process is forcibly terminated.

## During the two-week pilot

Invite 5–10 consenting adults. Cap each participant's success sample at their first 10 completed style reads. Do not tune the style definition mid-pilot. Monitor durable queue health and support withdrawal, export, correction and deletion requests promptly. Stop invitations on any correctness, privacy, isolation or durability uncertainty.

## Decision

Report participant-level distributions, not pooled game counts. The predeclared signal is a median of at least 70% “yes” responses and at least half of exit respondents choosing to continue. Missing responses, withdrawals and operational incidents remain visible. This pilot can justify a larger validation round; it cannot prove chess improvement, clinical efficacy, or general population fit.
