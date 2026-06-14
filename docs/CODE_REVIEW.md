# Code review guide (humans + AI)

How to review Sarce PRs without fighting the product. Complements [PHILOSOPHY.md](./PHILOSOPHY.md), [QUALITY_GATES.md](./QUALITY_GATES.md), and automated tests.

## Review stack

```
PHILOSOPHY.md + ADRs          ← product law
        ↓
CI (pytest, lint, build)      ← hard gates
        ↓
Greptile (.greptile/)         ← AI review with foundation lock
        ↓
Human reviewer                ← scope, UX, ADR judgment
```

Greptile is configured via `.greptile/` at repo root plus scoped configs in `apps/api/` and `apps/web/`. It reads this file and the docs listed in `.greptile/files.json`.

---

## Foundations — do not change without ADR

| Foundation | Why locked |
|------------|------------|
| **Brilliant** as first-class move tier | Core style identity signal |
| **Brilliant %** as headline metric | ADR [0001](./adr/0001-style-over-accuracy.md) |
| Rule-based classification (Phase 1) | No ML without ADR |
| Stockfish server-side only | Security + consistency |
| Engine as mirror, not judge | Philosophy |
| Encouraging UX copy | CI `philosophy-check` enforces |

If a PR or Greptile comment suggests changing any of these, **stop** — require `docs/adr/NNNN-*.md` before merge.

---

## High-value review targets

### Security (always flag)

- `SUPABASE_SERVICE_ROLE_KEY` in client code or `NEXT_PUBLIC_*`
- New Postgres tables without RLS
- User input passed to Stockfish path or shell
- Missing validation on import/analyze endpoints

### Architecture (flag if violated)

- Stockfish/`chess.engine` imports in `apps/api/app/routers/`
- Business logic in routers instead of `services/`
- Direct Supabase service role from `apps/web`
- Breaking `brilliantPct` / baseline API shape without migration plan

### Philosophy / UX (flag)

- Copy that shames style play
- Demoting Brilliant gauge or timeline on dashboard
- Competitive leaderboards or public ranking

### Database (flag)

- Dropping `brilliant` from quality constraints
- `style_vectors` changes without `version` bump

---

## Push back on (common false positives)

Greptile and reviewers should **not** treat these as required fixes:

| Suggestion | Response |
|------------|----------|
| "Rewrite brilliant detection with ML" | Phase 1 is heuristic; needs ADR |
| "Brilliant heuristics are wrong" | Tunable via `.env`; needs failing test or golden regression |
| "Add Redis/Celery for analysis" | Phase 1 uses `BackgroundTasks`; local-first |
| "Analyze opponent moves too" | User moves only is intentional |
| "Replace Brilliant % with accuracy" | Violates ADR 0001 |
| "Merge Brilliant into Best" | Violates philosophy |

---

## Greptile configuration

| File | Role |
|------|------|
| `.greptile/config.json` | Strictness, ignore patterns, foundation rules (IDs) |
| `.greptile/rules.md` | Prose guardrails for AI reviewer |
| `.greptile/files.json` | Docs and key source files Greptile must read |
| `apps/api/.greptile/config.json` | API-specific rules (routers thin, persist eval) |
| `apps/web/.greptile/config.json` | Web-specific rules (gauge, no secrets) |

Rule IDs in `config.json` (e.g. `foundation-no-remove-brilliant`) can be disabled in child configs only when intentionally scoped — **never** disable foundation rules at repo root.

### Install Greptile (maintainer)

1. Install [Greptile GitHub App](https://www.greptile.com/) on `meibaku/sarce`
2. Enable PR reviews on the repo
3. After 2–3 PRs with low false-positive rate, optionally add Greptile as a required check in the ruleset

Do **not** make Greptile a required merge check until foundation rules are validated on real PRs.

---

## Human reviewer checklist

Use with [.github/pull_request_template.md](../.github/pull_request_template.md):

1. Phase scope matches [PRODUCT_SPEC.md](./PRODUCT_SPEC.md)
2. Greptile comments on foundations are dismissed with ADR link or fixed
3. `npm run ci` equivalent passed in GitHub Actions
4. Classification changes: author ran `npm run test:golden` locally if Stockfish available
5. New dependencies justified and minimal

---

## Resolving Greptile disagreements

| Greptile says | You should |
|---------------|------------|
| Security issue (RLS, secrets) | Fix unless false positive — verify in code |
| Foundation change suggested | Reject; point to `.greptile/rules.md` |
| Style/heuristic "bug" in `brilliant.py` | Ask for test case; default keep heuristic |
| Out-of-phase feature (video, Lichess) | Defer to [PRODUCT_SPEC.md](./PRODUCT_SPEC.md) backlog |
| Valid refactor in scope | Accept if minimal and matches conventions |

For iterative Greptile tuning on a PR, use the project's greploop workflow after pushing fixes.
