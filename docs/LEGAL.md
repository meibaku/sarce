# Sarce — Licensing, third-party terms and privacy

**Status:** working notes (2026-10-22). **Not legal advice.** These notes list what to check and decide
before a public or paid launch. Get a lawyer to confirm the items marked ⚖️.

## 1. Sarce's own licence (ADR 0006)

- Sarce is **AGPL-3.0-only**. Anyone may use, self-host and modify it. Whoever runs a *modified* Sarce for
  others over a network must offer those users the source (section 13).
- **As the copyright holder, you aren't bound by your own licence.** That only holds while you own all the
  code. Today, CONTRIBUTING.md accepts contributions "under the AGPL-3.0" with no further grant, so after the
  first outside contribution:
  - any hosted Sarce that includes that code must offer its source to its users like anyone else;
  - you can't relicense, dual-license, or keep paid features closed in any work that includes or is combined
    with that contribution without the contributor's consent. Modules you wrote alone and that don't include
    it stay yours, but keeping that separation clean is hard in practice, so have counsel confirm the
    intended architecture;
  - the App Store problem below gets harder.
- **Recommendation:** add a Contributor Licence Agreement (CLA) now, while you're the only author. Either an
  Apache-style individual CLA, or a lighter DCO plus a licence grant to you. Use a CLA bot on PRs. ⚖️

### Distributing binaries (Sarce Node, mobile builds)

- **Sarce Node bundles Stockfish (GPL-3.0) and Sarce (AGPL-3.0).** Ship the licence texts and a written offer
  or link to the exact corresponding source (the tagged Sarce commit and the Stockfish release).
- **The App Store and GPL-family licences** are a known conflict. Apple's terms add restrictions the GPL
  forbids; VLC was pulled from the store in 2011 over this. The Expo app bundles only Sarce code and
  permissive (MIT/BSD/Apache) libraries; python-chess and Stockfish stay on the server. So as sole copyright
  holder you can publish it under your own terms. A CLA keeps it that way. ⚖️

### Trademark

- AGPL covers code, not the name. Register **"Sarce"** and the rook mark as trademarks, at least in Tanzania
  (BRELA) and in the main markets you launch in. Then forks must rename. ⚖️
- Add a short `TRADEMARKS.md`: the code is free to fork, but the name and logo aren't.

## 2. Dependencies and data

| Component | Licence / terms | What it means for Sarce |
| --- | --- | --- |
| Stockfish | GPL-3.0 | Runs as a separate program on the server: no change. Distributing it (Node, WASM) requires a source offer. |
| python-chess | GPL-3.0+ | Compatible with AGPL (ADR 0006); server-side only. |
| Maia-2 | MIT | Fine anywhere, including bundled. |
| Maia-3 | AGPL | Rejected in ADR 0002; would only be usable as a separate process. |
| Lichess open database and evaluation database | CC0 | Free to use, store and redistribute. Attribution isn't required but is good manners. |
| Lichess API | Lichess API terms | Make one request at a time and respect `429`. Cloud-eval is for occasional positions only. Use OAuth for anything signed-in. |
| Chess.com Published-Data API | Chess.com's PubAPI page | Read-only, public data only. Set a `User-Agent` with contact info. `services/chess_com.py` sends it on the archive-list request, but game downloads still send a plain `Sarce/0.1`; fix that before any hosted use. See §3. |
| pgnmentor.com reference games | Site terms | Game scores are facts; the collection is pgnmentor's. Sarce stores derived axis values and selected positions only. Don't redistribute the PGN files. |
| YouTube transcripts | YouTube Terms of Service | Already private per user (PRODUCT_SPEC Phase 2). Never pool or republish transcript text. |
| Claude API (vision, summaries) | Anthropic terms | Opt-in already. Say in the privacy notice that screenshots and transcripts go to Anthropic for processing. |

## 3. Chess.com and Lichess — staying a good layer on top

Sarce is a companion. Players keep playing on Chess.com and Lichess. To stay welcome there:

- **Post-game only.** This is already an invariant: never analyse an unfinished game. If a browser extension
  is ever built, it must refuse to act on a live game page. Opponent prep from public past games is normal
  and allowed; anything during a game breaks both sites' fair-play rules.
- **Chess.com IP.** Chess.com's PubAPI page asks developers to respect its IP and names "move classification
  glyphs", board palettes, piece sets and sounds. Sarce's badges use the classical annotation symbols
  (!!, !?, ?!, ?) in Sarce's own colours and shapes (`components/ui/move-badge.tsx`). Keep it that way: no
  teal starburst, nothing that copies their look.
- **The word "Brilliant"** is ordinary chess vocabulary (!! has meant brilliant for over a century), but
  label it as **Sarce's** Brilliant ([REVIEW_2026-10.md](./REVIEW_2026-10.md) §4).
- **Before charging money**, email `legal@chess.com` with a short description: a read-only companion,
  post-game only, no scraping, PubAPI only. Ask whether commercial use of PubAPI data needs anything more.
  Keep the reply on file. ⚖️
- Don't imply endorsement: no "for Chess.com" in the name, and no use of their logos.

## 4. Privacy and data protection

Sarce stores players' games, ratings, notes, intent answers, saved video positions and, for opponent prep,
reports built from *other* players' public games.

### Tanzania — Personal Data Protection Act, 2022

Most relevant while the operator is in Dar es Salaam. ⚖️ Confirm everything below with local counsel:

- **Registration:** data controllers and processors must register with the Personal Data Protection
  Commission (PDPC); registration lasts five years.
- **Cross-border transfers:** if Supabase or the servers are outside Tanzania, transfers need an adequate
  destination or safeguards, and a PDPC permit. Pick the hosting region with this in mind.
- **Children's data** is sensitive personal data. A minor's data needs prior written consent from a parent or
  guardian.
- **Duties:**
  - purpose limitation and data minimisation;
  - honour access, erasure and rectification requests;
  - appoint a Data Protection Officer;
  - notify the PDPC of breaches promptly.

### Other regions

If you serve the EU/UK or the US:

- **GDPR / UK GDPR:** you need a lawful basis, a privacy notice and erasure. Record the lawful basis for each
  processing purpose separately. For opponent profiling, legitimate interests is one candidate, but it needs a
  documented purpose, necessity and balancing assessment before it can be relied on. ⚖️
- **COPPA (US, under 13).**

### What the product should do before launch

1. **Minimum age.** Under Tanzania's PDPA a minor's data needs a parent's or guardian's prior consent, and
   Tanzanian law treats under-18s as children. So launch **18+** unless verified guardian consent is built for
   every under-18 user. Elsewhere the threshold may be lower (for example 16, or 13 with parental consent),
   but the strictest market you serve sets it. Chess has many junior players; don't build scouting reports on
   accounts you know are minors. ⚖️
2. **Privacy notice plus in-app data export and deletion.** "Delete my account" must also remove derived data:
   style vectors, lens scores, scouting reports about you, and shared links.
3. **Scouting reports profile third parties.** Keep them private to the requester; never publish or share them
   publicly. Keep the "no third-party names" rule for shared links, which already exists. Let any player ask
   to be excluded.
4. **Retention:** expire cached data you don't need, such as raw transcript snippets once summarised (if the
   user agrees).
5. **Processors:** keep a list (Supabase, the hosting provider, Anthropic, the payment provider) with data
   processing agreements.

## 5. Payments (when the paid tier starts)

- Subscriptions bought *inside* the iOS/Android apps must use Apple's or Google's billing, which takes a cut.
  Web checkout avoids that, within each store's current rules.
- For East Africa, offer mobile money through a local payment aggregator, and cards through an international
  provider. Check which providers support a Tanzanian business before choosing.
- Register the business and handle tax (VAT on digital services) in Tanzania first. ⚖️

## Checklist

- [ ] CLA or DCO added to CONTRIBUTING.md and enforced on PRs
- [ ] TRADEMARKS.md, and "Sarce" registered where you launch
- [ ] Email to legal@chess.com answered and filed
- [ ] Privacy notice, minimum age, export and delete flows
- [ ] PDPC registration; hosting region and transfer permit decided
- [ ] Source-offer text for Sarce Node and any binary release
