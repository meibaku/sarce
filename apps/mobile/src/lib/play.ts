/** Play's choices, the same as apps/web/src/components/play/play-view.tsx. */
import type { BotId } from "@sarce/types";

export const INTENTS: [string, string][] = [
  ["sacrifice", "Look for a sacrifice"],
  ["calm", "Stay calm when attacked"],
  ["solid", "Just play solid"],
];

export const BOTS: { id: BotId; label: string; why: string }[] = [
  { id: "defender", label: "Defender · 1600", why: "it defends like players at your rating, so your sacrifices meet realistic replies." },
  { id: "tal", label: "Tal-style attacker", why: "it plays the sound move that sets you the hardest problem, the way Tal liked to." },
  { id: "swindler", label: "Swindler", why: "it takes bigger risks to make you find the only move. Good practice for staying calm." },
];
