# Sarce — Complete Product Specification & Build Roadmap

**Project:** Sarce (repo: [meibaku/sarce](https://github.com/meibaku/sarce))  
**User:** Dratius  
**Primary goal:** Build a personal chess companion that helps you develop a Mikhail Tal-inspired playing style — aggressive, sacrificial, tactical — with a target of **6–10% Brilliant** moves per game.

**Philosophy:** Chess apps today focus on *"what is the engine's best move?"* Sarce focuses on *"are you playing the kind of chess you want to play?"* It is a **style-development tool**, not a judge. See [PHILOSOPHY.md](./PHILOSOPHY.md) for the product constitution.

**Related docs:**

| Doc | Role |
|-----|------|
| [PHILOSOPHY.md](./PHILOSOPHY.md) | Non-negotiable product principles |
| [PHASES.md](./PHASES.md) | Implementation status tracker |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Local-first technical design |
| [QUALITY_GATES.md](./QUALITY_GATES.md) | CI, tests, branch rules |

---

## Vision (north star)

Over time, Sarce becomes a **living record of your chess identity**:

- Your games and move-quality patterns over time
- Positions you explored from videos that inspired you
- The reasoning behind those moments (transcript + your own intent notes)
- Reference benchmarks from players whose style you admire

Less *"study harder"* — more *"play like the player you're becoming."*

---

## Phase 1 — MVP: Import, Brilliant Detection & Baseline Tracking

**Status:** ✅ **Complete** (v0.1.0)

### 1.1 Game import

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Fetch recent games from Chess.com by username | ✅ | `POST /games/import`, `ChessComClient` |
| Parse PGNs via `python-chess` | ✅ | `pgn_parser.py`, `game_store.py` |
| Store games + metadata in Postgres | ✅ | `games` table (date, opponent, rating, time control, result) |
| ECO opening code | 🔲 | Schema-ready; not yet extracted |
| Lichess support | 🔲 | Phase 4+ |

### 1.2 Move classification engine (rule-based, no ML)

For each **user move**, run Stockfish at depth ~18 before and after. Compute eval delta and bucket into Chess.com-style tiers:

| Tier | Rule |
|------|------|
| Best | Minimal centipawn loss |
| Excellent / Good | Threshold bands |
| Inaccuracy / Mistake / Blunder | Increasing centipawn loss |
| Miss | Had winning advantage, lost it |
| **Brilliant** | Tal-specific logic (see 1.3) |

**Status:** ✅ `move_classifier.py`, `stockfish.py`  
Raw eval data stored per move in `game_moves` for threshold tuning.

### 1.3 Brilliant move detection (Tal-specific)

A move is **Brilliant** when **ALL** hold:

1. **Material sacrifice** — piece value given up without immediate compensation
2. **Eval tightness** — position after move within ~0.3 of best alternative (`BRILLIANT_EVAL_MARGIN`)
3. **Position context** — not already winning by large margin (`BRILLIANT_WINNING_MARGIN`, default 3.0 pawns)
4. **Not forced** — more than one reasonable legal option existed

**Status:** ✅ `brilliant.py` — `is_brilliant` flag + eval data on each move

### 1.4 Baseline calculation & dashboard

| Requirement | Status |
|-------------|--------|
| Per-game Brilliant % + full distribution | ✅ `game_analyses` |
| Rolling baseline (last N games) | ✅ `user_baselines` |
| Headline Brilliant % gauge (6–10% target band) | ✅ `BrilliantGauge` |
| Plain-language style summary | ✅ `StyleSummary` |
| Full move-quality breakdown | ✅ `DistributionChart` |
| Brilliant % over time (line chart) | ✅ `BrilliantTimeline` |

**Status:** ✅ Dashboard wired to live API

### 1.5 Tal reference benchmark

| Requirement | Status |
|-------------|--------|
| Source Tal games from pgnmentor.com | ✅ `reference.py` |
| Batch classify sample, cache results | ✅ `process_tal_benchmark.py` |
| Display "Your style vs Tal" on dashboard | ✅ `/reference/tal` |

### Phase 1 deliverables — done

- ✅ Next.js frontend with dashboard
- ✅ FastAPI backend: Chess.com, Stockfish, Postgres (Supabase)
- ✅ Local-first dev; Docker-ready backend path documented
- ✅ Import games → see Brilliant % tracked over time
- ✅ pytest + CI + philosophy/architecture gates
- 🔲 **Android app** — planned client (Expo) on same API; web ships first

### Phase 1 API (live)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/games/import` | Import + analyze |
| GET | `/games` | List games |
| GET | `/games/moments` | Recent Brilliant/miss/blunder style moments |
| GET | `/games/{id}` | Game detail with classified moves |
| POST | `/games/analyze` | Analyze pending |
| GET | `/analysis/baseline/{id}` | Rolling baseline |
| GET | `/analysis/timeline/{id}` | Brilliant % over time |
| GET | `/reference/tal` | Tal benchmark |

---

## Phase 2 — Video Position Capture & Transcript Context

**Status:** 🔲 Planned

**Goal:** Capture positions from chess videos, attach commentary context, build a searchable personal library of explored ideas.

### 2.1 Manual position setter (quick win)

- Interactive board UI (`react-chessboard`) — drag pieces, clear, undo/redo
- Output FEN when position is set
- Feed into existing Stockfish analysis from Phase 1

### 2.2 Screenshot-to-position recognition

- Image upload/paste from video frames
- Open-source board recognition (CNN piece classifier, 8×8 grid)
- Output FEN → analysis board
- Confidence threshold → flag uncertain squares for manual correction

### 2.3 YouTube transcript integration (narrative layer)

- On save: capture video URL + timestamp
- Fetch captions (`youtube-transcript-api` or YouTube API)
- Extract commentary ~30s before to ~15s after timestamp
- Store transcript snippet with FEN in Postgres

### 2.4 AI-summarized annotations

- Condense transcript snippet via LLM (e.g. Claude API)
- 1–2 sentence summary: *"Commentator explains this rook sacrifice opens the 7th rank attack"*
- Permanent annotation on saved position
- Browse/search personal position library

### Phase 2 deliverables

- Manual position setter in app
- Screenshot recognition (proof of concept)
- Save positions from videos with transcript-derived context
- Searchable library of explored positions + annotations

### Schema notes (to add)

- `saved_positions` (fen, source_url, timestamp, transcript_raw, annotation_summary)
- `position_tags` for search/filter

---

## Phase 3 — Move Intent Narratives (Personal Chess Journal)

**Status:** 🔲 Planned

**Goal:** Connect engine classification with *your* stated intent — a journal of who you're becoming as a player.

### 3.1 Post-game annotation flow

- After import + analysis, prompt on high-stakes moves (sacrifices, attacks, risky positions)
- Prompt: *"Walk me through this move — what were you calculating? Intentional or intuitive?"*
- User writes 1–3 sentences per flagged move
- Store intent narrative alongside eval + classification

### 3.2 Intent vs. reality comparison

- For each annotated Brilliant move: user intent + engine eval
- Tags: **"You knew what you were doing"** vs **"You flew blind (but it worked)"**
- Patterns over time: calculated vs intuitive by phase of game

### 3.3 Personal chess journal view

Chronological library per game:

- Metadata (opponent, date, result, time control)
- Move-quality distribution + Brilliant %
- Brilliant moves with intent narratives
- Linked video positions (Phase 2) where applicable
- Search/filter: date, opponent rating, opening, Brilliant count, intent type

### 3.4 Narrative export

- Export game as Markdown or PDF: tree, annotations, intent notes
- Personal archive / sharing game reviews

### Phase 3 deliverables

- Post-game narrative prompt flow
- Intent/eval comparison on dashboard
- Searchable personal chess journal
- Living record: patterns + intent + video context

### Schema notes (to add)

- `move_annotations` (game_id, ply, user_intent, intent_type: calculated|intuitive)
- Extend `game_moves` or link via foreign key

---

## Phase 4+ — Future Enhancements (not locked)

| Feature | Description | Priority |
|---------|-------------|----------|
| **4.1 Lichess integration** | Import from Lichess API; unified Brilliant % across platforms | Medium |
| **4.2 Reference player comparison** | Compare style to admired players (Chess.com username); similarity score | Medium — schema exists |
| **4.3 Opening repertoire matcher** | Which openings produce most Brilliant %; style-aligned suggestions | Low |
| **4.4 Anonymized peer comparison** | "Players targeting Tal-style average 5.2% — you're at 7.1%" | Low — no public leaderboard |
| **4.5 Endgame tablebases** | Lichess tablebase eval on saved positions (≤7 pieces) | Low |
| **4.6 Browser extension** | YouTube hotkey → crop board → pre-load in app | Low |
| **4.7 GM training mode** | Hide Tal's next move; user guesses; reveal + transcript | Medium |
| **4.8 Android / mobile** | Expo app as primary client; same FastAPI backend | High |
| **4.9 Adjustable style goals** | User-defined target Brilliant %, risk profile | Medium — `profiles.style_goal` exists |
| **4.10 Per-move highlight view** | Where move diverged from style goal | Medium |

---

## Tech stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Frontend (web)** | Next.js, React, TypeScript, Tailwind | Dashboard, future board UI |
| **Frontend (mobile)** | Expo / React Native (Phase 4+) | Android-first |
| **Backend** | Python, FastAPI | Import, analysis, classification |
| **Chess logic** | `python-chess` | PGN, board state |
| **Engine** | Stockfish (server-side) | Depth ~18; local binary in dev |
| **Database & auth** | Supabase (Postgres + RLS) | Local via `supabase start` |
| **Game data** | Chess.com public API | Phase 1; Lichess Phase 4+ |
| **AI / summaries** | Claude API (Phase 2+) | Transcript condensing |
| **Deployment** | Docker (API), Vercel or similar (web) | Local-first until ready |

---

## Key design decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Rule-based Brilliant detection, not ML | Explainable; tunable against Tal corpus |
| 2 | Personal, not shared by default | Video transcripts + intent notes stay private |
| 3 | Lightweight narrative tone | "Reflect on your style" — not homework |
| 4 | Phased rollout | Phases 1–3 = complete product; 4+ organic |
| 5 | Style vector versioned | `style_vectors.version` — schema evolves safely |
| 6 | Engine as mirror, not judge | ADR-0001; enforced in CI |
| 7 | Local-first development | Stockfish + Supabase local; no cloud required for dev |

---

## Success metrics

| Phase | Success criterion |
|-------|-------------------|
| **Phase 1** | Import a game; see Brilliant % vs baseline; know if you played your target style |
| **Phase 2** | Explore video positions with transcript context; searchable library |
| **Phase 3** | Personal journal with intent + engine reality; awareness of calculated vs intuitive play |
| **User goal** | Sustain **6–10% Brilliant** while understanding *why* each sacrifice was made |

---

## Build order (Cursor)

```
✅ 1. Scaffold monorepo + Supabase + docs + CI gates
✅ 2. Chess.com import + PGN storage
✅ 3. Stockfish pipeline + move classification
✅ 4. Baseline + dashboard UI
✅ 5. Tal reference benchmark
🔲 6. Manual position setter (Phase 2.1)
🔲 7. YouTube transcript + position library (Phase 2.3–2.4)
🔲 8. Post-game intent narratives (Phase 3.1)
🔲 9. Chess journal view (Phase 3.3)
🔲 10. Android app (Expo) — when web flow is stable
```

---

## Document history

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-13 | Initial consolidated spec; Phase 1 marked complete |

*This document is the master product reference. Implementation status lives in [PHASES.md](./PHASES.md). Architectural changes require [ADRs](./adr/).*
