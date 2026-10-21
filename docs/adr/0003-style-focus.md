# ADR 0003 — Style focus picker

## Status

Superseded by [ADR 0005](./0005-retire-lab-dashboard.md)

## Context

[CHAOS_PLAN.md](../CHAOS_PLAN.md) (M8) asks for a style picker: "users choose their lens; dashboard
mirrors that identity." [ADR 0001](./0001-style-over-accuracy.md) and
[PHILOSOPHY.md](../PHILOSOPHY.md) fix **Brilliant %** as the headline dashboard metric, and CI checks
that the Brilliant gauge stays on the dashboard.

Letting a chosen lens replace the headline would contradict ADR 0001.

## Decision

1. Add a **style focus** — `brilliant` (default) or `chaos` — chosen on the dashboard and stored on
   the device (`localStorage`). No account or schema change.
2. The focus only changes **emphasis**: with `chaos`, the Chaos control panel moves up to sit directly
   under the header. Nothing is removed.
3. **Brilliant % remains the headline metric** and the gauge stays where it is, for every focus.

## Not decided here

Making the headline itself follow the chosen lens. That would supersede part of ADR 0001 and should
wait until the chaos numbers are validated (M4) — an uncalibrated score is not a fit headline.

## Consequences

### Positive

- A first, reversible step toward lens identity without touching a locked foundation.
- No data model change; the choice is private to the device.

### Negative / trade-offs

- The focus is not synced across devices until profiles carry it.
- "Mirrors that identity" is only partly met: emphasis, not the headline.

## Philosophy alignment

Aligned: personal rather than competitive, and the headline metric is untouched.

## Gates affected

None. `philosophy-check` still requires `BrilliantGauge` and `brilliantPct` on the dashboard.
