# Sarce mobile (Expo)

The phone app from the v1.0 design handoff: Home, Review, You, Train and Play tabs, plus Summary, the
sacrifice library, the weekly recap, Settings, onboarding and games against Sarce bots. It talks to the
same API as the web app and keeps nothing on a server of its own.

## Run it

1. Start the API (`npm run dev:api` from the repo root, or your own install).
2. Point the app at it. `localhost` works in a browser and the iOS simulator; a phone needs your computer's
   address on the same network:

   ```bash
   cd apps/mobile
   npm ci
   EXPO_PUBLIC_API_URL=http://192.168.1.20:8001 npx expo start
   ```

3. Scan the QR code with Expo Go, or press `i` / `a` for a simulator, or `w` for the browser. In the
   browser, add the dev origin to the API's `CORS_ORIGINS` if you changed its port (8081 is allowed by
   default).

Builds for the stores go through EAS (`npx eas-cli@latest build`); icons and the splash come from the
design handoff (`assets/`).

## Mascot

The rook mascot uses the handoff's motion maths unchanged (`src/lib/mascot-frames.ts`), drawn with
`react-native-svg`; with the system's Reduce Motion on it holds each state's still pose.

## Journal and prep

Settings → Export journal shares the Markdown journal through the system share sheet (save it to Files,
mail it, or print it to PDF from there). Opponent prep is reached from Play.
