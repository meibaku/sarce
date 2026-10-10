# Quality Gates & CI

How Sarce stays true to [PHILOSOPHY.md](./PHILOSOPHY.md) as the codebase grows.

## Gate layers

```
┌─────────────────────────────────────────────────────────────┐
│  Gate 0 — Philosophy        docs/PHILOSOPHY.md + ADRs        │
├─────────────────────────────────────────────────────────────┤
│  Gate 1 — CI (every PR)     lint → unit → arch → build      │
├─────────────────────────────────────────────────────────────┤
│  Gate 1.5 — Greptile        .greptile/ foundation lock      │
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
| **security-gates** | `npm run ci:security` | Committed secret, or a critical npm advisory |

GitHub Actions: `.github/workflows/ci.yml` — runs on pushes and PRs for both `staging` and `main`.

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

## Gate 1.5 — Greptile (AI review, foundation lock)

Configured in `.greptile/` — see [CODE_REVIEW.md](./CODE_REVIEW.md).

| File | Purpose |
|------|---------|
| `.greptile/config.json` | Strictness 2, ignore patterns, rule IDs for foundations |
| `.greptile/rules.md` | What Greptile must not suggest changing |
| `.greptile/files.json` | PHILOSOPHY, PRODUCT_SPEC, ADR, key services |
| `apps/api/.greptile/config.json` | Routers thin, eval persistence |
| `apps/web/.greptile/config.json` | Brilliant gauge, no client secrets |

**Foundation rules (high severity):** no removing Brilliant tier, no replacing Brilliant % headline, no ML Phase 1, Stockfish server-only, no punitive UX, ADR required for philosophy changes.

Greptile complements CI — it does **not** replace `test_philosophy_contracts.py` or `test_architecture.py`.

**Not required for merge yet.** Add as ruleset check only after 2–3 PRs validate low false-positive rate.

---

## Gate 6 — Human review (PR template)

Reviewers confirm:

- [ ] Does not frame style play as failure
- [ ] Brilliant % remains headline metric (if UI touched)
- [ ] Style vector version bumped if schema changed
- [ ] ADR added if contradicting PHILOSOPHY.md
- [ ] Greptile foundation comments dismissed or addressed (see CODE_REVIEW.md)

---

## Branch protection & rulesets (GitHub)

Sarce uses **two mechanisms** — you should prefer **Rulesets** (modern) over classic branch protection.

### Current state

| Branch | Ruleset config | Notes |
|--------|----------------|-------|
| `staging` (default branch, default PR target) | `.github/rulesets/staging.json` | Conversation resolution not required |
| `main` (releases) | `.github/rulesets/main.json` | Conversation resolution required |

`main.json` targets `refs/heads/main` explicitly. It used to target `~DEFAULT_BRANCH`, which silently
moved the protection to `staging` when the default branch changed and left `main` unprotected.

`.github/branch-protection.json` (classic protection) is kept only as a fallback; rulesets are canonical.

### Rules enforced (both rulesets)

| Rule | Setting |
|------|---------|
| Require PR before merge | ✅ |
| Required status checks | `api-test`, `web-lint`, `web-build`, `migration-check`, `philosophy-check`, `security-gates` |
| Branches must be up to date | ✅ (strict) |
| Require conversation resolution | ✅ (`main` only) |
| Block branch deletion | ✅ (ruleset only) |
| Block force push / non-fast-forward | ✅ |
| Enforce for admins | ✅ |

### Apply rulesets

The repo files are the source of truth; applying them is a manual, admin-only step.

```powershell
# main — creates or updates the "Protect main" ruleset
.\.github\scriptspply-ruleset.ps1

# staging — create once
gh api -X POST repos/meibaku/sarce/rulesets --input .github/rulesets/staging.json
```

Apply only after the CI workflow that reports `security-gates` is on the target branch — a required
check that never reports blocks every merge.

Verify: https://github.com/meibaku/sarce/settings/rules

### Re-apply classic protection (fallback)

```powershell
.\.github\scripts\apply-branch-protection.ps1
```

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
npm run ci:security     # secret scan + critical npm advisories
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
