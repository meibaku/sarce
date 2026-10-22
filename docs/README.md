# Sarce documentation

> **Start here:** [PHILOSOPHY.md](./PHILOSOPHY.md) — why Sarce exists and what it will never become.

## Product

| Doc | Purpose |
|-----|---------|
| [PRODUCT_SPEC.md](./PRODUCT_SPEC.md) | **Master spec** — Phases 1–4+, roadmap, success metrics |
| [PHILOSOPHY.md](./PHILOSOPHY.md) | Product constitution — style over accuracy |
| [PHASES.md](./PHASES.md) | Phase 1–3 roadmap and status |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Local-first system design |
| [QUALITY_GATES.md](./QUALITY_GATES.md) | CI, tests, branch rules, rulesets |
| [CODE_REVIEW.md](./CODE_REVIEW.md) | Human + Greptile review; foundation guardrails |
| [CHAOS_PLAN.md](./CHAOS_PLAN.md) | Chaos lens milestones M0–M8 |
| [VALIDATION.md](./VALIDATION.md) | M4 chaos validation results |
| [REVIEW_2026-10.md](./REVIEW_2026-10.md) | Trajectory and maths review, findings F1–F11, next six weeks |
| [BENCHMARK.md](./BENCHMARK.md) | Lichess and Chess.com comparison, cost, style pilot |
| [COMPUTE.md](./COMPUTE.md) | Analysis cost model; cache, Sarce Node, browser, cloud |
| [LEGAL.md](./LEGAL.md) | Licensing, third-party terms, privacy (not legal advice) |
| [SUSTAINABILITY.md](./SUSTAINABILITY.md) | How Sarce pays for itself |
| [adr/](./adr/) | Architecture Decision Records |

## Repository root

| File | Purpose |
|------|---------|
| [../README.md](../README.md) | Project overview and quick start |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | How to contribute |
| [../SECURITY.md](../SECURITY.md) | Vulnerability reporting |
| [../CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | Community standards |
| [../CHANGELOG.md](../CHANGELOG.md) | Version history |
| [../LICENSE](../LICENSE) | GNU AGPL-3.0 (ADR 0006) |

## API

| File | Purpose |
|------|---------|
| [../apps/api/README.md](../apps/api/README.md) | Backend setup and endpoints |

## ADRs

| ADR | Decision |
|-----|----------|
| [0001-style-over-accuracy.md](./adr/0001-style-over-accuracy.md) | Brilliant % headline; engine as mirror |
| [0002-human-model.md](./adr/0002-human-model.md) | Maia-2 as the human model |
| [0003-style-focus.md](./adr/0003-style-focus.md) | Style focus picker |
| [0004-brilliant-find-rate.md](./adr/0004-brilliant-find-rate.md) | Brilliant must be hard to find |
| [0005-retire-lab-dashboard.md](./adr/0005-retire-lab-dashboard.md) | Retire `/lab` |
| [0006-licence-agpl.md](./adr/0006-licence-agpl.md) | AGPL-3.0 |
| [0007-brilliant-real-offer.md](./adr/0007-brilliant-real-offer.md) | Brilliant needs a real offer |
| [0008-analysis-off-server.md](./adr/0008-analysis-off-server.md) | *Proposed:* analysis on the player's device |

New ADRs: use [0000-template.md](./adr/0000-template.md).
