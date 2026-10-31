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

## During the two-week pilot

Invite 5–10 consenting adults. Cap each participant's success sample at their first 10 completed style reads. Do not tune the style definition mid-pilot. Monitor durable queue health and support withdrawal, export, correction and deletion requests promptly. Stop invitations on any correctness, privacy, isolation or durability uncertainty.

## Decision

Report participant-level distributions, not pooled game counts. The predeclared signal is a median of at least 70% “yes” responses and at least half of exit respondents choosing to continue. Missing responses, withdrawals and operational incidents remain visible. This pilot can justify a larger validation round; it cannot prove chess improvement, clinical efficacy, or general population fit.
