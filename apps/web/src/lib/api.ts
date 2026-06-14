const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api/backend";
const LOCAL_USER_ID =
  process.env.NEXT_PUBLIC_LOCAL_USER_ID ??
  "00000000-0000-4000-8000-000000000001";

export async function fetchApi<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

export async function importChessComGames(username: string) {
  return fetchApi<{ imported: number; message: string; username: string }>(
    "/games/import",
    {
      method: "POST",
      body: JSON.stringify({ username, analyze: false }),
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

export async function listStyleMoments(username?: string) {
  const params = username
    ? `?username=${encodeURIComponent(username)}`
    : "";
  return fetchApi<{
    moments: import("@/types/chess").StyleMoment[];
  }>(`/games/moments${params}`);
}

export { LOCAL_USER_ID };
