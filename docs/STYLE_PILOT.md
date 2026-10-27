# Style pilot — admission contract

Status: implementation contract. Recruitment stays closed until the evidence file says `ready`.

## Purpose and scope

The first hosted pilot asks one narrow question: **does Sarce's post-game Brilliant read feel like the player it
describes?** It is an invite-only, web-only study for 5–10 adults over two weeks. Each participant plays where they
already play, imports only completed games, and answers at least ten style reads or is reported as incomplete.

The admitted surface is Brilliant percentage and its interval, the personal next band, move classification, recent
moments, Summary, Review, saved positions and journal. In `PILOT_MODE=style_v1`, unvalidated lenses and their derived
experiences are unavailable: chaos/fingerprint axes, focus, quests, traps, opponent preparation and reference-player
comparisons. They are not merely hidden in navigation; the API rejects them too.

Learning Evidence Phase 2 is a separate experiment. Its PR stack, assignments, item bank and efficacy endpoints do
not enter this release.

## Participants and consent

- One-use invitation, verified Supabase sign-in and explicit consent are required.
- Participants confirm they are at least 18. No junior, school or coach cohort is admitted.
- Consent binds the protocol and privacy-notice versions shown at enrolment.
- Withdrawal stops imports, analysis, feedback and new sessions immediately.
- Export and deletion remain available after withdrawal.

No recruitment starts until the owner records the Tanzania PDPC/cross-border basis for the selected Singapore
processors. This document is an engineering gate, not legal advice.

## Measures

After a style read, the participant answers `yes`, `partly` or `no` to “Did this read sound like you?” and may add a
500-character comment. The exit survey records whether they would continue (`yes`, `maybe`, `no`), the most valuable
and least trusted capability, and non-binding willingness to pay (`yes`, `maybe`, `no`). It collects no payment data.

Report each participant first: completed reads, resonance rate and Wilson interval. Then report the median participant
rate. A high-volume player never receives more weight than another participant.

## Decision and safety gates

The pilot is a positive signal when the median participant reaches at least 70% `yes`, at least half would continue,
and no tenant-isolation, consent, deletion, durability or material analysis failure occurred. With 5–10 people this is
not statistical efficacy evidence.

Stop admission immediately for cross-tenant access, an acknowledged-but-unpersisted answer, incomplete deletion
reported as complete, loss of accepted feedback, analysis of an unfinished game, or a material privacy/consent error.
Pause new invitations for a failed backup restore, unavailable authoritative Maia model, growing oldest-job age, or
an unresolved production migration mismatch.

## Release admission

The exact candidate SHA must have green CI, Stockfish golden tests, hosted authentication and tenant-isolation smoke,
import-to-review E2E evidence, export/delete evidence, a successful isolated restore, desktop and narrow-mobile browser
QA, rollback instructions, and signed owner/legal gates. Deploy the same reviewed artifact that passed admission.
