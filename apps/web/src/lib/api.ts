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

export async function analyzePendingGames(username?: string, limit?: number) {
  return fetchApi<{ message: string; username: string | null; userId: string }>(
    "/games/analyze",
    {
      method: "POST",
      body: JSON.stringify({ username, limit }),
    },
  );
}

export async function getUserBaseline(username?: string) {
  const params = username ? `?username=${encodeURIComponent(username)}` : "";
  return fetchApi<import("@/types/chess").UserBaseline>(
    `/analysis/baseline/${LOCAL_USER_ID}${params}`,
  );
}

export async function getTimeline(username?: string) {
  const params = username ? `?username=${encodeURIComponent(username)}` : "";
  return fetchApi<{ points: import("@/types/chess").TimelinePoint[] }>(
    `/analysis/timeline/${LOCAL_USER_ID}${params}`,
  );
}

export async function getTalBenchmark() {
  return fetchApi<import("@/types/chess").ReferenceBenchmark>(
    "/reference/tal",
  );
}

export async function listGames(username?: string) {
  const params = username
    ? `?username=${encodeURIComponent(username)}`
    : "";
  return fetchApi<{ games: import("@/types/chess").GameSummary[] }>(
    `/games${params}`,
  );
}

export async function getStyleProfile(username?: string) {
  const params = username ? `?username=${encodeURIComponent(username)}` : "";
  return fetchApi<import("@/types/chess").StyleProfile>(
    `/analysis/style-profile/${LOCAL_USER_ID}${params}`,
  );
}

export async function getGameDetail(gameId: string, username?: string) {
  const params = username ? `?username=${encodeURIComponent(username)}` : "";
  return fetchApi<import("@/types/chess").GameDetail>(
    `/games/${gameId}${params}`,
  );
}

export async function listStyleMoments(username?: string) {
  const params = username
    ? `?username=${encodeURIComponent(username)}`
    : "";
  return fetchApi<{
    moments: import("@/types/chess").StyleMoment[];
  }>(`/games/moments${params}`);
}

export async function getGameLenses(gameId: string) {
  return fetchApi<import("@/types/chess").GameLenses>(`/games/${gameId}/lenses`);
}

export async function getChaosSummary(username: string) {
  return fetchApi<import("@/types/chess").ChaosSummary>(
    `/users/${encodeURIComponent(username)}/chaos-summary`,
  );
}

export async function listTraps(band?: number) {
  const params = band == null ? "" : `?band=${band}`;
  return fetchApi<{ traps: import("@/types/chess").Trap[] }>(`/traps${params}`);
}

export async function getGameIdeas(gameId: string) {
  return fetchApi<import("@/types/chess").GameIdeas>(`/games/${gameId}/ideas`);
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

export async function getHome(username?: string) {
  const params = username ? `?username=${encodeURIComponent(username)}` : "";
  return fetchApi<import("@/types/chess").HomeApi>(`/users/home${params}`);
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

export async function getTrain() {
  return fetchApi<import("@/types/chess").TrainApi>(`/users/train`);
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

export async function getBots() {
  return fetchApi<{ bots: { id: import("@/types/chess").BotId; label: string; why: string }[] }>(`/play/bots`);
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

export async function getSyncStatus() {
  return fetchApi<import("@/types/chess").SyncStatus>(`/users/sync`);
}

export async function syncNow() {
  return fetchApi<{ started: boolean }>(`/users/sync`, { method: "POST" });
}
