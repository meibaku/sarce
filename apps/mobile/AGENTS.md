# apps/mobile — agent notes

The Expo (React Native) app: the v1.0 design's phone screens on the same FastAPI API as `apps/web`.
Read the root `AGENTS.md` first; its domain invariants apply here too (post-game only, no punitive copy,
Brilliant % is the headline, Stockfish stays server-side).

- **Expo SDK 58.** Expo changes between SDKs: check the versioned docs
  (`https://docs.expo.dev/versions/v58.0.0/`) before using an Expo or React Native API, and add packages with
  `npx expo install <pkg>` so versions match the SDK.
- **Own lockfile.** This app is not in the root npm workspace, so React Native's dependency tree never
  touches the web build. Run `npm ci` here.
- **Routes** live in `src/app/` (Expo Router); components in `src/components/`; the API client, tokens and
  hooks in `src/lib/`. Response types are shared from `apps/web/src/types/chess.ts` via `@sarce/types`
  with **type-only** imports, so nothing from the web app is bundled.
- **Design rules** are the web's (`docs/DESIGN.md`): one filled accent button per screen, outlined choices,
  accent-text links, no red, no shadows, IBM Plex.
- Native folders (`ios/`, `android/`) are generated; configure `app.json` instead.

```bash
npm run typecheck   # tsc --noEmit
npm run lint        # expo lint
npx expo start      # Expo Go / simulators; add --web for the browser
```
