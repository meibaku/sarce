# ADR 0006 — Licence: GNU AGPL-3.0

## Status

Accepted (2026-10-21).

## Context

Sarce started under MIT. The plan is to stay open source, keep self-hosting first-class, and later offer a
hosted (cloud) tier. A permissive licence would let anyone run a modified Sarce as a competing service
without sharing their changes. Two dependencies matter for compatibility: **python-chess is GPL-3.0+**
(already in the API), and Stockfish is GPL-3.0 (run as a separate binary). Maia-2 is MIT.

## Decision

License Sarce under the **GNU Affero General Public License v3.0** (`AGPL-3.0-only`, the official text in
`LICENSE`). The package manifests carry the SPDX identifier.

## Consequences

- Anyone may use, self-host and modify Sarce. Whoever runs a modified version for others over a network must
  offer those users the corresponding source (section 13), so improvements to a hosted Sarce come back.
- Compatible with python-chess (GPL-3.0+; AGPL-3.0 section 13 permits combining with GPLv3 code), with
  Stockfish as a separate program, and with the MIT/BSD/Apache dependencies of the web and mobile apps.
- Contributions are accepted under the same licence (CONTRIBUTING.md). Relicensing a cloud tier under other
  terms later needs the copyright holder's consent for all code, so keep contributions' provenance clear.
- Superseded option: PolyForm Noncommercial (branch `chore/licence-and-private-docs`) was not chosen; it is
  source-available rather than open source and conflicts with the GPL dependencies.

## Philosophy alignment

Aligned: local-first and self-hostable, with the community able to build on it.
