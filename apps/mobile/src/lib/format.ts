/** Display helpers, as the web's apps/web/src/lib/format.ts (the phone app imports only types from the web). */

export function timeAgo(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return "recently";
  const minutes = Math.round((now.getTime() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const RESULT = { win: "won", loss: "lost", draw: "drew" } as const;

export function gameMeta(game: {
  timeControl: string | null;
  userColor: "white" | "black" | null;
  opponent: string | null;
  result: "win" | "loss" | "draw" | null;
}): string {
  return [
    game.timeControl,
    game.userColor ? game.userColor[0].toUpperCase() + game.userColor.slice(1) : null,
    game.opponent ? `vs ${game.opponent}` : null,
    game.result ? RESULT[game.result] : null,
  ]
    .filter(Boolean)
    .join(" · ");
}
/** "19. Rxe5" for White, "23. …Qh4" for Black, from a 0-based ply over the whole game. */
export function moveLabel(ply: number, san: string | null): string {
  return `${Math.floor(ply / 2) + 1}. ${ply % 2 === 1 ? "…" : ""}${san ?? ""}`;
}
