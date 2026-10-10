# Changelog

All notable changes to Sarce are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Chaos Lens M1 (WDL + EP foundation): `services/ep.py`, node-limited MultiPV `StockfishEngine.analyse`,
  `position_evals` cache with adaptive MultiPV widening, per-ply clock parsing, and migration
  `20261010000000_position_evals.sql`. Off by default — set `POSITION_EVALS_ENABLED=true` after migrating
- Chaos Lens M0 housekeeping: `AGENTS.md`, `security-gates` CI job (secret scan + critical `npm audit`),
  `staging` ruleset config, promotion PR template, `pr:create` / `pr:promote` helpers
  (adapted from MeibakuHQ/ai-ci-repo-template)
- `docs/CHAOS_PLAN.md` — milestone plan for the chaos/survival style lenses (revised after review:
  complete safe sets, halfmove clock in cache keys, held-out validation set, `cook.py` is AGPL — reference only)
- `docs/PRODUCT_SPEC.md` — master product specification (Phases 1–4+)
- Phase 2 redefined: video position capture + transcript context
- Phase 3 redefined: move intent narratives + personal chess journal

### Changed
- CI and the philosophy check now run on pushes and PRs for `staging` as well as `main`
- `main` ruleset config targets `refs/heads/main` instead of the default branch
- `next` 15.5.19 → 15.5.27 and other in-range updates via `npm audit fix` (clears a critical advisory)

### Fixed
- Duplicate `listStyleMoments` export in `apps/web/src/lib/api.ts` that broke the web build

## [0.1.0] - 2026-06-13

### Added
- **Phase 1 MVP** — chess style analysis monorepo
- Next.js dashboard with Brilliant % gauge, distribution charts, timeline
- FastAPI backend: Chess.com import, Stockfish classification, Tal-style brilliant detection
- Supabase schema with RLS, style vectors, reference benchmarks
- Tal PGN benchmark batch job
- Local-first architecture (`docs/ARCHITECTURE.md`)
- Philosophy constitution (`docs/PHILOSOPHY.md`) and quality gates
- CI: api-test, web-lint, web-build, migration-check, philosophy-check
- GitHub ruleset "Protect main" with required PR + status checks
- Dependabot, CODEOWNERS, issue/PR templates
- pytest suite (unit, architecture, philosophy contracts, golden Stockfish)

[Unreleased]: https://github.com/meibaku/sarce/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/meibaku/sarce/releases/tag/v0.1.0
