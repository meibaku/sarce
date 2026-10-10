"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { authConfigured } from "@/lib/auth";
import { createClient } from "@/lib/supabase/client";

/** Header control: who is signed in, with sign in / sign out. Hidden when auth is not configured. */
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
        className="rounded-md border border-accent/40 px-3 py-1.5 text-sm text-accent transition hover:border-accent"
      >
        Sign in
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-foreground/60">{email}</span>
      <button
        type="button"
        onClick={async () => {
          await createClient().auth.signOut();
          window.location.reload();
        }}
        className="rounded-md border border-white/15 px-3 py-1.5 text-foreground/70 transition hover:border-white/30"
      >
        Sign out
      </button>
    </div>
  );
}
