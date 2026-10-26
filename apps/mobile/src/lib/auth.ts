/** Native Supabase session storage and passwordless deep-link completion. */
import * as SecureStore from "expo-secure-store";
import { createClient } from "@supabase/supabase-js";

const url = process.env.EXPO_PUBLIC_SUPABASE_URL;
const key = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

const storage = {
  getItem: (name: string) => SecureStore.getItemAsync(name),
  setItem: (name: string, value: string) => SecureStore.setItemAsync(name, value),
  removeItem: (name: string) => SecureStore.deleteItemAsync(name),
};

export const authConfigured = Boolean(url && key);
export const supabase = authConfigured
  ? createClient(url!, key!, {
      auth: { storage, autoRefreshToken: true, persistSession: true, detectSessionInUrl: false },
    })
  : null;

export async function getAccessToken(): Promise<string | null> {
  return (await supabase?.auth.getSession())?.data.session?.access_token ?? null;
}

export async function sendSignInLink(email: string, redirectTo: string): Promise<void> {
  if (!supabase) throw new Error("Sign-in is not configured");
  const { error } = await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: redirectTo } });
  if (error) throw error;
}

export async function consumeAuthUrl(authUrl: string): Promise<boolean> {
  if (!supabase) return false;
  const params = new URLSearchParams(authUrl.split("#", 2)[1] ?? authUrl.split("?", 2)[1] ?? "");
  const accessToken = params.get("access_token");
  const refreshToken = params.get("refresh_token");
  if (!accessToken || !refreshToken) return false;
  const { error } = await supabase.auth.setSession({ access_token: accessToken, refresh_token: refreshToken });
  if (error) throw error;
  return true;
}
