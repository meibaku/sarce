# Do the nine traits overlap? (review F10a)

Implementation plan item 1.9. Measured 2026-10-24 with `scripts/trait_overlap.py` on the owner's 1,639 analysed
games, cut into 81 consecutive windows of 20 games. Each window's traits are computed exactly as the You screen
does (under 30 events a value is dashed). Pearson's r is taken per pair over the windows where both have a value.

|            | Sacrifice | Chaos | Calm | Initiative | Defence | Grip | Fight | Clock | Foresight |
| ---------- | --------: | ----: | ---: | ---------: | ------: | ---: | ----: | ----: | --------: |
| Sacrifice  |           | −0.07 | −0.29 |      0.17 |   −0.24 | −0.14 | −0.26 |  0.08 |     −0.18 |
| Chaos      |           |       | 0.00 |       0.68 |   −0.28 | −0.60 |  0.18 |  0.33 |     −0.31 |
| Calm       |           |       |      |      −0.35 |    0.50 |  0.39 | −0.07 | −0.03 |      0.34 |
| Initiative |           |       |      |            |   −0.49 | −0.77 |  0.26 |  0.29 |     −0.55 |
| Defence    |           |       |      |            |         |  0.59 |  0.11 | −0.05 |      0.60 |
| Grip       |           |       |      |            |         |       |  0.16 | −0.20 |      0.68 |
| Fight      |           |       |      |            |         |       |       |  0.11 |      0.03 |
| Clock      |           |       |      |            |         |       |       |       |     −0.08 |

Fight has a value in 35 windows (it needs 30 moves made while clearly losing); every other trait in all 81.

## What it says

- **No pair moves together** above |r| = 0.8, so nothing is merged or dropped and no ADR is needed.
- The strongest links are Initiative–Grip (−0.77) and Chaos–Initiative (0.68). Initiative is the mean chaos score,
  so it shares Chaos's inputs. The two still differ: Chaos counts how often you set a problem, Initiative how big
  the problems are. The negative link with Grip is a real style trade-off: weeks spent setting problems are not
  weeks spent quietly converting.
- A calm cluster shows up: Defence, Grip, Foresight and Calm correlate 0.34–0.68 with each other. That is
  expected, since they are four sides of solid play, and none is close to a duplicate.
- **Calm's ceiling:** Calm ranges 0.71–0.85 across windows (median 0.78), a narrow band but not a flat one. The
  fingerprint scales every trait to its own range (`you.heat_levels`), so the band still reads as changes from
  week to week. No rescale is needed.

## Re-run

```bash
cd apps/api
python -m scripts.trait_overlap --window 20
```

Re-check after a lens changes meaning (for example review F8 moved four lenses to expected points) and once the
reference players are rescored (plan 2.1). The references can then join the matrix.
