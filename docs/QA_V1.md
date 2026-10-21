# v1.0 visual and accessibility QA

Final pass on the released v1.0 build (2026-10-21) against the design handoff (`meibaku/sarce-private`,
`design/handoff-v1/screenshots`). Each screen was captured at the handoff frame size with headless Edge and diffed
pixel by pixel (a pixel counts as different when any channel differs by more than 40/255). Web screens use the
`/preview/*` routes, which render the handoff's sample data.

## Pixel diff

| Screen | Desktop 1280×832 | Phone 390×844 (web) |
| --- | --- | --- |
| Onboarding | 2.2% | 6.3% |
| Home | 2.4% | 7.1% |
| Summary | 4.0% | 6.4% |
| Review | 3.8% | 6.1% |
| You | 3.5% | 9.7% |
| Library | 2.0% | 8.0% |
| Recap | 2.8% | 6.8% |
| Train | 4.0% | 11.6% |
| Play | 3.3% | 7.8% |
| Settings | 4.7% | 7.3% |
| Edge states | 1.3% | — |

Side-by-side review of the largest differences found no layout, type, colour or radius drift. The remaining
differences are text antialiasing, a few pixels of vertical offset from the handoff's simulated status bar, and
features added after the handoff:

- Train: the "Save a position from a video, screenshot or book" link (PHASES 2.2), which moves the queue down.
- You: Tal's marker uses his scored values, and the trend marker reads "new Brilliant rule" (ADR 0007).

The Expo app renders the same screens (checked in the browser pane at 390×844). Headless Edge captures it blank
before its fonts load, so its pixel numbers are not recorded here.

## Accessibility

- **Focus:** every interactive element shows a 2px accent outline offset by 2px (`:focus-visible`, `globals.css`).
- **Reduced motion:** `prefers-reduced-motion: reduce` cuts transitions and animations to 0.01ms. Settings → Motion
  can also force Reduced.
- **Touch targets:** at 390px every control is at least 44×44 to the touch.
  - Web: the controls drawn smaller than 44px use the `.tap` utility, an invisible centred hit area. These are the
    header Settings button, text links, steppers and compact toggles. Recap's game bars fill their 72px column.
  - Expo: the back arrow and the steppers use `hitSlop`. The native `Switch` is sized by the OS.
