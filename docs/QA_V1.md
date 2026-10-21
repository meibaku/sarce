# v1.0 visual and accessibility QA

Final pass on the v1.0 build (2026-10-21/22) against the design handoff (`meibaku/sarce-private`,
`design/handoff-v1/screenshots`). Each screen was captured at the handoff frame size and diffed pixel by pixel (a
pixel counts as different when any channel differs by more than 40/255). Every screen was also reviewed side by
side with its handoff frame, not just the worst.

- **Web:** the `/preview/*` routes render the handoff's sample data. Desktop was captured with headless Edge at
  1280×832. Phone was captured at 390×844 @2x inside a 390px frame, because headless Edge enforces a window wider
  than a phone.
- **Phone app (Expo):** captured through the DevTools protocol with a forced 390×844 @2x mobile viewport, against
  real local data. Its numbers therefore include content that differs from the handoff's samples, such as
  opponents, counts and Brilliant %.

## Results

| Screen | Web 1280×832 | Web 390×844 | Expo 390×844 | Side-by-side notes |
| --- | --- | --- | --- | --- |
| Onboarding | 2.2% | 6.3% | 5.2% | Same 4 steps and copy. Expo: no tab bar on this pushed screen. |
| Home | 2.4% | 7.1% | 11.2%* | Matches. Expo: real data. |
| Summary | 4.0% | 6.4% | — | Matches (the Expo summary is reached from Home). |
| Review | 3.8% | 6.1% | 9.7%* | Matches. Web adds "All games" (after the handoff). Expo: real game. |
| You | 3.5% | 9.7% | 14.2%* | Tal marker uses his scored values; the trend marker reads "new Brilliant rule" (ADR 0007). Expo: the chaos map card shows while You data loads. |
| Library | 2.0% | 8.0% | 7.8%* | Matches. Expo: 20 rows, then "Show all", so the detail card stays reachable. |
| Recap | 2.8% | 6.8% | 12.2%* | Matches. Expo: this week's real games. |
| Train | 4.0% | 11.6% | 11.8%* | The video-position link (PHASES 2.2) moves the queue down. Expo: real queue, including chaos-map drills. |
| Play | 2.6% | 8.1% | 7.9% | Matches. Opponent prep, added after the handoff, sits after the handoff's three cards. |
| Settings | 4.7% | 7.3% | 7.2% | Web adds rows added after the handoff (video help, export). Expo: theme row says dark is planned for v1.1. |
| Edge states | 1.3% | — | — | Matches. |

\* Mostly real data rather than the handoff samples.

Remaining differences across all screens are text antialiasing and a few pixels of vertical offset from the
handoff's simulated status bar. No layout, type, colour or radius drift was found.

### Fixed during this pass

- **Expo board:** each row wrapped after seven squares, so the board showed stripes instead of a checkerboard. It
  now lays out rank rows inside the border, with file letters underneath.
- **Expo icons and header:** the tab bar and header used text glyphs (⌂ ⌕ ◯ ↻ ▷ ⚙). They now use the handoff's line
  icons and rook mark (react-native-svg), and the tab labels are no longer clipped.
- **Expo screens brought in line with the handoff:**
  - Home: latest-game card and Brilliant gauge.
  - Review: header and round badges.
  - Train: queue rows, with "Up next" then Start.
  - Recap: streak card, bars and boxes.
  - Library: "← You" link and detail card.
  - Play: warm-up card and bot chips.
  - Onboarding: all four steps.
  - Settings: the full style-goal and question labels, plus the theme row.
- **Web Play:** the Opponent prep card had displaced the Sarce bot card from its handoff position.

### Platform difference kept on purpose

The Expo app opens Library, Recap, Settings and Onboarding as pushed screens with a back arrow and no tab bar. That
is the native navigation pattern; the handoff draws them as tab-bar pages.

## Accessibility

- **Focus:** every interactive element shows a 2px accent outline offset by 2px (`:focus-visible`, `globals.css`).
- **Reduced motion:** `prefers-reduced-motion: reduce` cuts transitions and animations to 0.01ms. Settings → Motion
  can also force Reduced.
- **Touch targets:** at 390px every control is at least 44×44 to the touch.
  - Web: the controls drawn smaller than 44px use the `.tap` utility, an invisible centred hit area. These are the
    header Settings button, text links, steppers and compact toggles. Recap's game bars fill their 72px column.
  - Expo: the back arrow, header Settings button, steppers, bot and filter chips use `hitSlop`. The native `Switch`
    is sized by the OS.
