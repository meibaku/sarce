"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { authConfigured } from "@/lib/auth";
import { createClient } from "@/lib/supabase/client";

/** Settings row: who is signed in, with sign in / sign out. Hidden when auth is not configured (local-first). */
export function AuthStatus() {
  const [email, setEmail] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!authConfigured()) return;
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? null);
      setReady(true);
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setEmail(session?.user.email ?? null);
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  if (!ready) return null;

  if (!email) {
    return (
      <Link
        href="/login"
        className="text-[13px] font-medium text-accent-text"
      >
        Sign in
      </Link>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-3 text-[13px]">
      <span className="text-ink-2">Signed in as {email}</span>
      <button
        type="button"
        onClick={async () => {
          await createClient().auth.signOut();
          window.location.reload();
        }}
        className="text-[13px] font-medium text-accent-text"
      >
        Sign out
      </button>
    </div>
  );
}
