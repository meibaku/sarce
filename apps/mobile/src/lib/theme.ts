/**
 * v1.0 design tokens (docs/DESIGN.md), the same values as apps/web/src/app/globals.css.
 * Light only; no red, no shadows. Fonts are IBM Plex Sans / Mono, loaded in app/_layout.tsx.
 */
export const color = {
  ink: "#1a1f26",
  ink2: "#3c434e",
  muted: "#59616d",
  faint: "#69717d",
  line: "#e2e5e9",
  line2: "#d8dce1",
  line3: "#c8ced5",
  hair: "#f0f2f4",
  page: "#fafbfc",
  panel: "#f5f7fa",
  surface: "#ffffff",
  accent: "#2f5f9e",
  accentPress: "#22446f",
  accentText: "#2a5590",
  accentTint: "#eef3fa",
  sound: "#2f7a55",
  checkin: "#9a6420",
  boardDark: "#eef1f5",
} as const;

export const font = {
  sans: "IBMPlexSans_400Regular",
  medium: "IBMPlexSans_500Medium",
  semibold: "IBMPlexSans_600SemiBold",
  mono: "IBMPlexMono_400Regular",
  monoMedium: "IBMPlexMono_500Medium",
} as const;

/** The fingerprint heat ramp, cells 0–7. */
export const ramp = ["#f5f7fa", "#e6edf6", "#d3e0f0", "#b9cde6", "#97b4d8", "#7096c4", "#4f7ab0", "#2f5f9e"];
