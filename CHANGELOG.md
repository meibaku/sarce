# Changelog

All notable changes to Sarce are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- `docs/PRODUCT_SPEC.md` — master product specification (Phases 1–4+)
- Phase 2 redefined: video position capture + transcript context
- Phase 3 redefined: move intent narratives + personal chess journal

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
