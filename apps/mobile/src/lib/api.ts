/**
 * The Sarce API client for the app: the same endpoints as apps/web/src/lib/api.ts, with the response
 * types shared from the web app (type-only imports, so nothing from apps/web is bundled).
 * EXPO_PUBLIC_API_URL points at the API: localhost works for web and the iOS simulator; a phone on
 * the same network needs the computer's LAN address (e.g. http://192.168.1.20:8001).
 */
import type {
  BotId,
  BotPosition,
  CheckinAnswer,
  Confidence,
  DrillCheck,
  FeltAnswer,
  FocusKind,
  HomeApi,
  IntentType,
  RecapApi,
  ScoutingReport,
  ReviewApi,
  SacrificeRow,
  SettingsApi,
  SummaryApi,
  SyncStatus,
  TrainApi,
  YouApi,
} from "@sarce/types";

export const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8001";
/** Where shared links open (the web app's /s/<token> page). */
export const WEB_BASE = process.env.EXPO_PUBLIC_WEB_URL ?? "http://localhost:3001";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

const post = (body: unknown) => ({ method: "POST", body: JSON.stringify(body) });
const put = (body: unknown) => ({ method: "PUT", body: JSON.stringify(body) });

export const getHome = () => api<HomeApi>("/users/home");
export const getSummary = (id: string) => api<SummaryApi>(`/games/${id}/summary`);
export const setFelt = (id: string, answer: FeltAnswer) => api(`/games/${id}/felt`, post({ answer }));
export const answerCheckin = (id: string, ply: number, answer: CheckinAnswer, flagged: boolean) =>
  api(`/games/${id}/checkin`, post({ ply, answer, flagged }));
export const getReview = (id: string) => api<ReviewApi>(`/games/${id}/review`);
export const saveIntent = (id: string, ply: number, intent: { type: IntentType | null; note: string }) =>
  api(`/games/${id}/moves/${ply}/intent`, put(intent));
export const savePosition = (body: { fen: string; title?: string; gameId?: string; ply?: number }) =>
  api<{ id: string }>("/users/positions", post(body));
export const getYou = () => api<YouApi>("/users/you");
export const getSacrifices = () => api<{ sacrifices: SacrificeRow[] }>("/users/sacrifices");
export const getRecap = () => api<RecapApi>("/users/recap");
export const getFocus = () => api<{ weekly: string | null; today: string | null }>("/users/focus");
export const setFocus = (kind: FocusKind, value: string) => api(`/users/focus`, put({ kind, value }));
/** `drill` (e.g. "defend:<game>:<ply>" from the library) goes to the front of the queue. */
export const getTrain = (drill?: string) => api<TrainApi>(`/users/train${drill ? `?drill=${encodeURIComponent(drill)}` : ""}`);
export const checkDrill = (fen: string, uci: string, answer: string | null, source: string) =>
  api<DrillCheck>("/users/train/check", post({ fen, uci, answer, source }));
export const answerDrill = (drillKey: string, confidence: Confidence) => api("/users/train/answer", post({ drillKey, confidence }));
export const startBot = () => api<BotPosition>("/play/start", { method: "POST" });
export const botMove = (fen: string, uci: string | null, bot: BotId, reply = true) =>
  api<BotPosition>("/play/move", post({ fen, uci, bot, elo: 1600, reply }));
export const saveBotGame = (body: { bot: BotId; moves: string[]; result: "win" | "loss" | "draw"; clocks_ms: number[] }) =>
  api<{ gameId: string }>("/play/save", post(body));
export const getSettings = () => api<SettingsApi>("/users/settings");
export const updateSettings = (changes: Partial<SettingsApi>) => api<SettingsApi>("/users/settings", put(changes));
export const getSync = () => api<SyncStatus>("/users/sync");
export const syncNow = () => api("/users/sync", { method: "POST" });
/** The journal as Markdown (Settings → Export journal, shared through the system share sheet). */
export async function getJournal(): Promise<string> {
  const res = await fetch(`${API_BASE}/users/journal`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.text();
}
export const listReports = () => api<{ reports: ScoutingReport[] }>("/scouting/reports");
export const createReport = (username: string, source: "chess_com" | "lichess") => api<ScoutingReport>("/scouting/reports", post({ username, source }));
export const deleteReport = (id: string) => api(`/scouting/reports/${id}`, { method: "DELETE" });
export const createShare = (kind: "summary" | "sacrifice", gameId: string, ply?: number) =>
  api<{ id: string; token: string }>("/shares", post({ kind, gameId, ply }));
/** "Why this move?" (the web's WhyApi in apps/web/src/lib/api.ts). */
export type WhyApi = {
  label: string;
  fenBefore: string;
  badge: string;
  isBrilliant: boolean;
  brilliant: { rule: string; passed: boolean; detail: string }[];
  chaos: { faced: boolean; pFail: number[] | null; rungs: number[]; safeReplies: string[] };
  lines: { title: string; note: string; eval: string; kind: string; steps: { san: string; fen: string }[] }[];
};
export const getWhy = (gameId: string, ply: number) => api<WhyApi>(`/games/${gameId}/moves/${ply}/why`);
/** Your chaos map (the web's ChaosMapPosition in apps/web/src/lib/api.ts). `problem` = P_fail × stake. */
export type ChaosMapPosition = {
  key: string;
  fen: string;
  line: string;
  seen: number;
  predictability: number | null;
  usual: { san: string; pFail: number | null; problem: number | null };
  chaos: { san: string; uci: string; pFail: number | null; problem: number | null };
  same: boolean;
  elo: number;
};
export const getChaosMap = () => api<{ positions: ChaosMapPosition[]; building: boolean }>("/users/chaos-map");
export const rebuildChaosMap = () => api<{ building: boolean }>("/users/chaos-map", { method: "POST" });
/** Your traps (the web's TrapSet in apps/web/src/lib/api.ts). */
export type TrapSet = { fen: string; line: string; move: string; seen: number; caught: number; rate: number; likely: number; gainPawns: number; slip: string; defence: string };
export const getTrapsSet = () => api<{ traps: TrapSet[]; building: boolean }>("/users/traps-set");
export const rebuildTrapsSet = () => api<{ building: boolean }>("/users/traps-set", { method: "POST" });
export const importGames = (site: "chess_com" | "lichess", username: string) =>
  api<{ imported: number }>(site === "lichess" ? "/games/import/lichess" : "/games/import", post({ username, analyze: true }));
