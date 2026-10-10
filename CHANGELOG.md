# Changelog

All notable changes to Sarce are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Chaos Lens M7 (UI): Ideas card in the game review — idea windows, what became of them, pivots, and
  motif chips for the selected move
- Chaos Lens M6 (trap atlas): `trap_atlas` table, `services/trap_atlas.py`, `scripts/build_trap_atlas.py`,
  `GET /traps`, and a Trap atlas panel with a drill mode. The atlas is empty until the validation
  sampler has been run on real games
- Chaos Lens M7 (intention tagger v1): engine-free motif detectors (`services/motifs.py`), idea windows
  with worked / refuted / fizzled verdicts and pivots (`services/ideas.py`), `move_tags` and `game_ideas`
  tables, `GET /games/{id}/ideas`. Off by default — set `IDEA_TAGGER_ENABLED=true` after migrating
- Chaos Lens M4 (tooling): `scripts/validate_chaos.py` and `services/chaos_validation.py` (stratified
  sampling, held-out split by game, calibration table, clock multiplier, baselines), plus
  `scripts/backfill_chaos.py` for games analysed before chaos data existed. The validation run itself
  is still to do — see `docs/VALIDATION.md`
- Chaos Lens M5 (review UI): chaos heat strip and key-move card in the game review (verdict badges,
  who-falls-for-it curve, clock), and a Chaos control panel on the dashboard
- Chaos Lens M3: `app/lenses/` (lens protocol, registry, soundness / chaos / survival lenses as pure
  functions), `move_lens_scores` table, `GET /games/{id}/lenses` and `GET /users/{u}/chaos-summary`
- Chaos Lens M2 (human model, part 1): `HumanModel` interface, `human_probs` cache table, the Elo ladder,
  and an interim engine-free heuristic model. The Maia-2 vs Maia-3 choice is still open — see
  `docs/adr/0002-human-model.md`
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
