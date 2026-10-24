import { getAccessToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api/backend";
const LOCAL_USER_ID =
  process.env.NEXT_PUBLIC_LOCAL_USER_ID ??
  "00000000-0000-4000-8000-000000000001";

export async function fetchApi<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const token = await getAccessToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      // Signed in: the API uses this verified identity and ignores any user id we send.
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

export async function importChessComGames(username: string, analyze = false) {
  return fetchApi<{ imported: number; message: string; username: string }>(
    "/games/import",
    {
      method: "POST",
      body: JSON.stringify({ username, analyze }),
    },
  );
}

export async function importLichessGames(username: string, analyze = false) {
  return fetchApi<{ imported: number; message: string; username: string }>(
    "/games/import/lichess",
    {
      method: "POST",
      body: JSON.stringify({ username, analyze }),
    },
  );
}

export async function listScoutingReports() {
  return fetchApi<{ reports: import("@/types/chess").ScoutingReport[] }>("/scouting/reports");
}

export async function createScoutingReport(username: string, source: "chess_com" | "lichess") {
  return fetchApi<import("@/types/chess").ScoutingReport>("/scouting/reports", {
    method: "POST",
    body: JSON.stringify({ username, source }),
  });
}

export async function deleteScoutingReport(id: string) {
  return fetchApi<{ deleted: number }>(`/scouting/reports/${id}`, { method: "DELETE" });
}

export { LOCAL_USER_ID };

/** `since`: your last visit (ISO); Home then also returns `session`, the games analysed after it. */
export async function getHome(username?: string, since?: string) {
  const params = new URLSearchParams();
  if (username) params.set("username", username);
  if (since) params.set("since", since);
  const query = params.toString();
  return fetchApi<import("@/types/chess").HomeApi>(`/users/home${query ? `?${query}` : ""}`);
}

export async function getGameSummary(gameId: string) {
  return fetchApi<import("@/types/chess").SummaryApi>(`/games/${gameId}/summary`);
}

export async function setGameFelt(gameId: string, answer: import("@/types/chess").FeltAnswer) {
  return fetchApi<{ gameId: string; felt: string }>(`/games/${gameId}/felt`, {
    method: "POST",
    body: JSON.stringify({ answer }),
  });
}

export async function getGameReview(gameId: string) {
  return fetchApi<import("@/types/chess").ReviewApi>(`/games/${gameId}/review`);
}

export async function saveMoveIntent(
  gameId: string,
  ply: number,
  intent: { type: import("@/types/chess").IntentType | null; note: string },
) {
  return fetchApi<{ type: string | null; note: string }>(`/games/${gameId}/moves/${ply}/intent`, {
    method: "PUT",
    body: JSON.stringify(intent),
  });
}

export async function getYou(username?: string) {
  const params = username ? `?username=${encodeURIComponent(username)}` : "";
  return fetchApi<import("@/types/chess").YouApi>(`/users/you${params}`);
}

export async function getSacrifices(username?: string) {
  const params = username ? `?username=${encodeURIComponent(username)}` : "";
  return fetchApi<{ sacrifices: import("@/types/chess").SacrificeRow[] }>(`/users/sacrifices${params}`);
}

export async function getRecap() {
  return fetchApi<import("@/types/chess").RecapApi>(`/users/recap`);
}

export async function getFocus() {
  return fetchApi<{
    weekly: string | null;
    today: string | null;
    focuses: Record<string, string>;
    intents: Record<string, string>;
  }>(`/users/focus`);
}

export async function setFocus(kind: import("@/types/chess").FocusKind, value: string) {
  return fetchApi<{ kind: string; value: string; label: string }>(`/users/focus`, {
    method: "PUT",
    body: JSON.stringify({ kind, value }),
  });
}

/** The Train queue; `drill` (a drill key) is put first, e.g. from the library's "Defend it yourself". */
export async function getTrain(drill?: string | null) {
  return fetchApi<import("@/types/chess").TrainApi>(`/users/train${drill ? `?drill=${encodeURIComponent(drill)}` : ""}`);
}

/** Keeps a position as a Train drill (Review → Add to Train, or from a video / screenshot / book). */
export async function savePosition(body: {
  fen: string;
  title?: string;
  note?: string;
  gameId?: string;
  ply?: number;
  sourceUrl?: string;
  sourceTimeS?: number;
  excerpt?: string;
  aiSummary?: string;
}) {
  return fetchApi<{ id: string }>(`/users/positions`, { method: "POST", body: JSON.stringify(body) });
}

/** Saved positions, optionally filtered by words in titles, notes and transcripts. */
export async function listPositions(q?: string) {
  return fetchApi<{ positions: import("@/types/chess").SavedPosition[] }>(`/users/positions${q ? `?q=${encodeURIComponent(q)}` : ""}`);
}

export async function deletePosition(id: string) {
  return fetchApi<{ deleted: string }>(`/users/positions/${id}`, { method: "DELETE" });
}

/** The captions around a moment of a YouTube video (no AI); `transcript` when YouTube blocks the fetch. */
export async function videoExcerpt(url: string, transcript?: string) {
  return fetchApi<{ videoId: string; at: number; text: string; start: number; end: number }>(`/videos/excerpt`, {
    method: "POST",
    body: JSON.stringify({ url, transcript }),
  });
}

/** Opt-in, sent to Claude: read a board from a screenshot. The FEN comes back checked. */
export async function fenFromImage(data: string, mediaType: string) {
  return fetchApi<{ fen: string; confidence: "high" | "medium" | "low"; notes: string; flipped: boolean }>(`/videos/fen-from-image`, {
    method: "POST",
    body: JSON.stringify({ data, mediaType }),
  });
}

/** Opt-in, sent to Claude: a short title, summary and ideas from what a commentator said. */
export async function summarizeExcerpt(excerpt: string, fen?: string) {
  return fetchApi<{ title: string; summary: string; ideas: string[] }>(`/videos/summary`, {
    method: "POST",
    body: JSON.stringify({ excerpt, fen }),
  });
}

export async function answerDrill(drillKey: string, confidence: import("@/types/chess").Confidence) {
  return fetchApi<{ drillKey: string; confidence: string; nextDue: string; inDays: number }>(`/users/train/answer`, {
    method: "POST",
    body: JSON.stringify({ drillKey, confidence }),
  });
}

export async function checkDrillMove(fen: string, uci: string, answer: string | null, source: string) {
  return fetchApi<import("@/types/chess").DrillCheck>(`/users/train/check`, {
    method: "POST",
    body: JSON.stringify({ fen, uci, answer, source }),
  });
}

/** Saves a finished bot game for review; its analysis starts in the background. */
export async function saveBotGame(body: {
  bot: import("@/types/chess").BotId;
  moves: string[];
  result: "win" | "loss" | "draw";
  clocks_ms: (number | null)[];
}) {
  return fetchApi<{ gameId: string }>(`/play/save`, { method: "POST", body: JSON.stringify(body) });
}

export async function startBotGame() {
  return fetchApi<import("@/types/chess").BotPosition>(`/play/start`, { method: "POST" });
}

export async function playBotMove(
  fen: string,
  uci: string | null,
  bot: import("@/types/chess").BotId,
  { elo = 1600, reply = true }: { elo?: number; reply?: boolean } = {},
) {
  return fetchApi<import("@/types/chess").BotPosition>(`/play/move`, {
    method: "POST",
    body: JSON.stringify({ fen, uci, bot, elo, reply }),
  });
}

export async function getSettings() {
  return fetchApi<import("@/types/chess").SettingsApi>(`/users/settings`);
}

export async function updateSettings(changes: Partial<import("@/types/chess").SettingsApi>) {
  return fetchApi<import("@/types/chess").SettingsApi>(`/users/settings`, {
    method: "PUT",
    body: JSON.stringify(changes),
  });
}

/** Downloads the journal as Markdown, sending the sign-in token like every other call. */
/** The journal as Markdown text (for the printable PDF view). */
export async function getJournalText() {
  const token = await getAccessToken();
  const res = await fetch(`${API_BASE}/users/journal`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  return res.text();
}

export async function downloadJournal() {
  const token = await getAccessToken();
  const res = await fetch(`${API_BASE}/users/journal`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const url = URL.createObjectURL(await res.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = "sarce-journal.md";
  link.click();
  URL.revokeObjectURL(url);
}

export async function answerCheckin(gameId: string, ply: number, answer: import("@/types/chess").CheckinAnswer, flagged: boolean) {
  return fetchApi<{ gameId: string; ply: number; answer: string }>(`/games/${gameId}/checkin`, {
    method: "POST",
    body: JSON.stringify({ ply, answer, flagged }),
  });
}

/** A shared link's public snapshot (GET /public/shares/{token}); no names, no notes, not live. */
export type PublicShare =
  | {
      kind: "summary";
      result: "win" | "loss" | "draw" | null;
      userColor: string | null;
      timeControl: string | null;
      headline: string;
      outcome: string | null;
      brilliant: { pct: number | null; count: number | null; of: number | null; goalLo: number | null; goalHi: number | null };
      moments: { label: string; glyph: string; line: string }[];
      styleRead: number | null;
      sharedAt: string;
    }
  | {
      kind: "sacrifice";
      fen: string;
      label: string;
      glyph: string;
      type: string;
      material: number;
      held: boolean;
      opening: string | null;
      playedAt: string | null;
      sharedAt: string;
    };

export interface SharedLink {
  id: string;
  token: string;
  kind: "summary" | "sacrifice";
  game_id: string | null;
  ply: number | null;
  created_at: string;
  revoked_at: string | null;
  snapshot: { headline?: string; label?: string };
}

/** A read-only link to one of your summaries or sacrifices. */
export async function createShare(kind: "summary" | "sacrifice", gameId: string, ply?: number) {
  return fetchApi<{ id: string; token: string; kind: string }>(`/shares`, { method: "POST", body: JSON.stringify({ kind, gameId, ply }) });
}

export async function listShares() {
  return fetchApi<{ links: SharedLink[] }>(`/shares`);
}

export async function revokeShare(id: string) {
  return fetchApi<{ revoked: string }>(`/shares/${id}`, { method: "DELETE" });
}

/** GET /games: newest first, or (chaos) the chaos-analysed games with the highest peak first. */
export interface GameListItem {
  id: string;
  playedAt: string | null;
  opponent: string | null;
  opponentRating: number | null;
  result: string | null;
  timeControl: string | null;
  analysisStatus: string | null;
  brilliantPct: number | null;
  chaosPeak?: number;
  realChaos?: number;
  cheapChaos?: number;
  calculatedRisk?: number;
}

export async function listGames(chaos: boolean, limit = 30) {
  return fetchApi<{ games: GameListItem[] }>(`/games?limit=${limit}${chaos ? "&chaos=true" : ""}`);
}

/** Public: anyone with the token. */
/** The Brilliant definition (plan 3.3), public: clauses in plain words and the thresholds the rule uses. */
export interface BrilliantDefinition {
  rule: string;
  clauses: { id: string; title: string; text: string }[];
  thresholds: Record<string, number>;
}

export async function getBrilliantDefinition() {
  return fetchApi<BrilliantDefinition>("/public/brilliant/definition");
}

export async function getPublicShare(token: string) {
  return fetchApi<PublicShare>(`/public/shares/${encodeURIComponent(token)}`);
}

/** GET /games/{id}/moves/{ply}/why (app/services/explain.py). */
export interface WhyApi {
  gameId: string;
  ply: number;
  label: string;
  fenBefore: string;
  orientation: "white" | "black";
  badge: string;
  isBrilliant: boolean;
  brilliant: { rule: string; passed: boolean; detail: string }[];
  evalBefore: number | null;
  evalAfter: number | null;
  best: string | null;
  chaos: { verdict: string | null; faced: boolean; pFail: number[] | null; rungs: number[]; safeReplies: string[] };
  lines: { title: string; note: string; eval: string; kind: "played" | "engine" | "brilliant"; steps: { san: string; uci: string; fen: string }[] }[];
}

/** "Why this move?": the badge's reason, the Brilliant checks with numbers, and playable lines. */
export async function getWhy(gameId: string, ply: number) {
  return fetchApi<WhyApi>(`/games/${gameId}/moves/${ply}/why`);
}

/** One position on the chaos map (app/services/chaos_map.py). `problem` = P_fail × stake. */
export interface ChaosMapPosition {
  fen: string;
  line: string;
  seen: number;
  predictability: number | null;
  usual: { san: string; pFail: number | null; stake: number | null; problem: number | null };
  chaos: { san: string; uci: string; pFail: number | null; stake: number | null; epLoss: number | null; problem: number | null };
  same: boolean;
  elo: number;
  computedAt: string;
}

/** Your chaos map: frequent opening positions and the sound move that asks the most of opponents. */
export async function getChaosMap() {
  return fetchApi<{ positions: ChaosMapPosition[]; building: boolean }>(`/users/chaos-map`);
}

/** One of your traps (app/services/traps_set.py): where opponents most often go wrong on the next move. */
export interface TrapSet {
  fen: string;
  line: string;
  move: string;
  seen: number;
  caught: number;
  rate: number;
  /** The rate we can stand behind: the 95% lower bound of caught/seen; traps are ranked by it. */
  likely: number;
  gainPawns: number;
  slip: string;
  defence: string;
}

export async function getTrapsSet() {
  return fetchApi<{ traps: TrapSet[]; building: boolean }>(`/users/traps-set`);
}

/** Rebuilds your traps in the background from stored evaluations; poll getTrapsSet until `building` is false. */
export async function rebuildTrapsSet() {
  return fetchApi<{ building: boolean }>(`/users/traps-set`, { method: "POST" });
}

/** Rebuilds the map in the background; poll getChaosMap until `building` is false. */
export async function rebuildChaosMap() {
  return fetchApi<{ building: boolean }>(`/users/chaos-map`, { method: "POST" });
}

export async function getSyncStatus() {
  return fetchApi<import("@/types/chess").SyncStatus>(`/users/sync`);
}

export async function syncNow() {
  return fetchApi<{ started: boolean }>(`/users/sync`, { method: "POST" });
}
