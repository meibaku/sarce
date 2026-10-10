import { createClient } from "@/lib/supabase/client";

/** True when the Supabase project is configured; without it the app stays local-first. */
export function authConfigured() {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  );
}

/** The signed-in user's access token, or null when signed out or auth is not configured. */
export async function getAccessToken(): Promise<string | null> {
  if (typeof window === "undefined" || !authConfigured()) return null;
  try {
    const { data } = await createClient().auth.getSession();
    return data.session?.access_token ?? null;
  } catch {
    return null;
  }
}
