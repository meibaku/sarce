# Quality Gates & CI

How Sarce stays true to [PHILOSOPHY.md](./PHILOSOPHY.md) as the codebase grows.

## Gate layers

```
┌─────────────────────────────────────────────────────────────┐
│  Gate 0 — Philosophy        docs/PHILOSOPHY.md + ADRs        │
├─────────────────────────────────────────────────────────────┤
│  Gate 1 — CI (every PR)     lint → unit → arch → build      │
├─────────────────────────────────────────────────────────────┤
│  Gate 2 — Contracts         API shape, schema, metrics      │
├─────────────────────────────────────────────────────────────┤
│  Gate 3 — Golden analysis   Stockfish tier regression       │
├─────────────────────────────────────────────────────────────┤
│  Gate 4 — E2E smoke         import → analyze → dashboard    │
├─────────────────────────────────────────────────────────────┤
│  Gate 5 — Release           Tal benchmark + manual UX pass  │
└─────────────────────────────────────────────────────────────┘
```

---

## Gate 1 — CI pipeline (required on every PR)

| Job | Command | Blocks merge if |
|-----|---------|-----------------|
| **api-test** | `pytest tests -v` | Any test fails |
| **api-arch** | `pytest tests/test_architecture.py tests/test_philosophy_contracts.py -v` | Boundary/philosophy violation |
| **web-lint** | `npm run lint:web` | ESLint errors |
| **web-build** | `npm run build:web` | TypeScript/build failure |
| **migration-check** | SQL files exist + parse | Broken migration syntax |

GitHub Actions: `.github/workflows/ci.yml`

Local equivalent:

```powershell
npm run ci
```

---

## Gate 2 — Philosophy contracts (automated)

`tests/test_philosophy_contracts.py` asserts:

- `MoveQuality` includes `brilliant` (style is first-class)
- Default target band is 6–10% Brilliant
- Baseline API returns `brilliantPct` as a top-level field
- `style_vector` schema has `version` field
- No Phase-1 ML dependencies (`sklearn`, `torch`, etc.)
- Classification produces all tiers, not only errors

---

## Gate 3 — Architecture tests (automated)

`tests/test_architecture.py` asserts:

- Routers are thin — no Stockfish imports in `routers/`
- Services own business logic — `brilliant.py`, `move_classifier.py` exist
- Config centralizes thresholds (`brilliant_eval_margin`, targets)
- Docs exist: `PHILOSOPHY.md`, `ARCHITECTURE.md`, `PHASES.md`
- `style_vectors` migration includes `version`

---

## Gate 4 — Golden analysis (optional in CI, required pre-release)

Marked `@pytest.mark.stockfish` — skipped in CI without engine, run locally:

```powershell
pytest tests/test_golden_analysis.py -m stockfish -v
```

Uses fixed PGN fixtures; asserts tier distribution is stable within tolerance.
Protects against accidental threshold changes that break Tal-style detection.

---

## Gate 5 — E2E smoke (Phase 1.5+)

When Supabase + API run in CI (or locally before release):

1. `POST /games/import` with test username
2. `POST /games/analyze`
3. `GET /analysis/baseline` — `brilliantPct` present
4. Dashboard renders gauge without error

---

## Gate 6 — Human review (PR template)

Reviewers confirm:

- [ ] Does not frame style play as failure
- [ ] Brilliant % remains headline metric (if UI touched)
- [ ] Style vector version bumped if schema changed
- [ ] ADR added if contradicting PHILOSOPHY.md

---

## Branch protection (GitHub)

Recommended for `main` — config in `.github/branch-protection.json`:

| Rule | Setting |
|------|---------|
| Require PR before merge | ✅ |
| Require status checks | `api-test`, `web-lint`, `web-build`, `migration-check`, `philosophy-check` |
| Require branches up to date | ✅ (strict) |
| Require conversation resolution | ✅ |
| Block force push | ✅ |
| Enforce for admins | ✅ |

**Apply automatically:**

```powershell
.\.github\scripts\apply-branch-protection.ps1
```

Or via GitHub Rulesets UI: import `.github/rulesets/main.json` at
Settings → Rules → Rulesets.

**Also configured:**

- `.github/CODEOWNERS` — philosophy/classification paths
- `.github/dependabot.yml` — weekly npm/pip updates
- `.github/workflows/philosophy-check.yml` — PR copy guard
- Issue templates with philosophy alignment checkboxes
- `SECURITY.md` — vulnerability reporting

---

## Local dev commands

```powershell
npm run ci              # full local gate
npm run test:api        # unit + arch + philosophy
npm run test:golden     # Stockfish regression (local only)
npm run lint:web        # Next.js ESLint
npm run build:web       # production build check
```

---

## When to add an ADR

Create `docs/adr/NNNN-title.md` when:

- Changing what Brilliant means
- Replacing Brilliant % as headline metric
- Adding ML-based classification
- Introducing competitive/social ranking
- Removing or merging style tiers

Template: `docs/adr/0000-template.md`
