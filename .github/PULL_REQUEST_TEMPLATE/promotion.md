## Promotion: `staging` → `main`

Release promotion PR. Confirm soak on `staging` is complete before merge.

## Release

- **Milestone:** <!-- e.g. Chaos Lens M1, or v0.2.0 -->
- **Tag after merge:** <!-- e.g. v0.2.0 -->

## Exit criteria

- [ ] CI green on the latest `staging` commit (`api-test`, `web-lint`, `web-build`, `migration-check`, `philosophy-check`, `security-gates`)
- [ ] `npm run test:golden` passes locally with Stockfish (Phase 1 tiers + Tal benchmark unchanged)
- [ ] Greptile / AI review findings on the included PRs are fixed or documented as non-actionable
- [ ] `CHANGELOG.md` and `docs/PHASES.md` reflect what is shipping

## Summary since last production release

<!-- High-level changelog -->

## Migrations

<!-- New files in supabase/migrations/ and the order to apply them, or "none" -->

## Rollback plan

<!-- How to revert if the release misbehaves -->
