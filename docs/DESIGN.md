# Design system (v1.0)

The UI follows the v1.0 design handoff. The full handoff (HTML prototypes, screenshots, motion and mascot
reference) lives in the private `meibaku/sarce-private` repo under `design/handoff-v1/`; this page keeps
the rules the code depends on.

**Status:** being implemented screen by screen (see `CHANGELOG.md`). Until a screen ships, the pre-v1
dashboard (moving to `/lab`) keeps its old dark palette; the tokens below take effect with the foundation
change. North star: **"Did this game feel like you, not did you play like the engine?"**

## Product rules the UI enforces

- **One filled accent button per screen** — the next step in the loop. Choices are outlined; everything
  else is an accent-text link.
- **At most one question per game** by default (Settings: None / One / Up to two).
- **Post-game only.** Play is against Sarce bots; nothing runs during games on other sites.
- **Honesty:** blitz and rapid chaos numbers carry an "uncalibrated" badge (validation covers 1+0 only).
  A metric based on fewer than 5 games is dashed and grey and never appears in a headline.
- **No red anywhere.** Sacrifices are never framed as failure: "unsound", never "cheap"; "didn't hold" is grey.

### Backend → UI copy

| Backend | UI |
| --- | --- |
| `real_chaos` | real problem |
| `cheap_chaos` | unsound chaos |
| `calculated_risk` | speculative (!?) |
| survival `survived` | safe reply found (✓) |
| survival `missed` | didn't hold (?) |

Phase 1 Inaccuracy / Mistake / Blunder labels never appear on style screens.

## Tokens

Defined once in `apps/web/src/app/globals.css` (Tailwind v4 `@theme`).

| Token | Hex | Use |
| --- | --- | --- |
| ink | `#1a1f26` | text, 1.5px outlines, piece outlines |
| ink-2 | `#3c434e` | body copy |
| muted | `#59616d` | secondary text, labels, "didn't hold" |
| faint | `#69717d` | tertiary text |
| line | `#e2e5e9` | card hairlines (1px) |
| line-2 | `#d8dce1` | inactive control outlines (1.5px), board grid |
| hair | `#f0f2f4` | row dividers |
| page | `#fafbfc` | app background |
| panel | `#f5f7fa` | inset blocks |
| surface | `#ffffff` | cards |
| accent | `#2f5f9e` (hover `#284f85`, active `#22446f`) | primary button, band, selection |
| accent-text | `#2a5590` | links, accent numbers |
| accent-tint | `#eef3fa` | selected background, band fill |
| sound | `#2f7a55` | ✓ badge |
| check-in | `#9a6420` | ?! badge, "uncalibrated" |
| board-dark | `#eef1f5` | dark squares |
| fingerprint 0–7 | `#f5f7fa #e6edf6 #d3e0f0 #b9cde6 #97b4d8 #7096c4 #4f7ab0 #2f5f9e` | heat cells |

**Type:** IBM Plex Sans 400/500/600 and IBM Plex Mono 400/500. One headline number per screen
(Mono 400, accent-text). Section labels: Sans 600 11px uppercase, 0.08em tracking, muted.

**Shape:** radius 6 (controls), 8 (cards), 4 (board). Strokes 1.5px (controls), 1px (hairlines),
1.75 (icons). No shadows. Focus: `outline: 2px solid #2f5f9e; outline-offset: 2px`.

**Layout:** phone frame 390 wide, desktop 1280; content padding 16 / 28–32; card gaps 12 / 18;
max width 1120. Grids use `repeat(auto-fit, minmax(min(100%, Npx), 1fr))`.

**Motion:** `cubic-bezier(.2,.7,.2,1)`; 120ms for hover/press/toggles, 220ms for panels and moment
changes. One celebration only: on a `!!` moment the logo's top lifts 4px over 600ms. Reduced motion
turns it into a fade.

## Assets

`apps/web/public/brand/`: the 7a "open break" rook mark (ink and white) and the app icon (white mark on
an accent tile). The app sets "sarce" as live IBM Plex text beside the mark; the handoff's wordmark SVG is not
shipped because its lettering is live text that changes font where Plex is missing. Outline it before any
brand use outside the app. `src/app/icon.png` and `apple-icon.png` are the favicons.
