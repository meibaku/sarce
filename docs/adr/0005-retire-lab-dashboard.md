# ADR 0005 — Retire the pre-v1 dashboard (`/lab`)

## Status

Accepted. Supersedes [ADR 0003](./0003-style-focus.md).

## Context

The v1.0 design handoff replaced the single dark dashboard with eleven screens around the core loop
(Home → Summary → Review → Train). The old dashboard stayed at `/lab` until every feature had a new home.
The CI philosophy check and `test_philosophy_contracts.py` pinned the Brilliant headline to
`components/dashboard.tsx`.

## Decision

1. Delete `/lab`, `components/dashboard.tsx` and the components only it used, and the `.theme-lab` palette.
2. Where each feature went:
   - import → onboarding and Settings (with automatic sync);
   - Brilliant gauge, timeline and Tal reference → Home and You;
   - chaos summary, chaos review and ideas → Home, Summary and Review;
   - style moments → Home and Summary moments;
   - trap atlas → Train ("trap at your band");
   - opponent scouting → **`/prep`**, reached from Play;
   - sign-in status → Settings.
   The raw move-quality distribution has no new home on purpose: style screens never show Phase 1
   labels (docs/DESIGN.md copy mapping).
3. ADR 0003's style focus (`brilliant` / `chaos`, emphasis only) is superseded by the weekly focus in
   Recap, which steers Train and Play. Brilliant % stays the headline everywhere, unchanged.
4. The headline contract moves to Home: CI checks that `components/home/home-view.tsx` renders the
   `StyleGauge` with Brilliant, and the contract tests check Home's copy and `gap_line` for punitive words.

## Consequences

- One design system; no second palette to keep working.
- The device-local style focus is gone; people who used it get the weekly focus instead.

## Philosophy alignment

Aligned: Brilliant % stays the headline and is still enforced by CI, now on the screen people actually see.

## Gates affected

`philosophy-check.yml` and `test_philosophy_contracts.py` now point at Home.
