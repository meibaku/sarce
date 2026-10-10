"use client";

import Link from "next/link";
import { useState } from "react";
import { authConfigured } from "@/lib/auth";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = (new FormData(event.currentTarget).get("email") as string).trim();
    if (!email) return;
    setBusy(true);
    setStatus(null);
    // Passwordless: Supabase emails a one-time link; no password is ever handled here.
    const { error } = await createClient().auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    setStatus(error ? error.message : "Check your email for the sign-in link.");
    setBusy(false);
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <p className="text-xs uppercase tracking-[0.2em] text-accent-muted">Chess style analysis</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight">Sign in to Sarce</h1>

      {!authConfigured() ? (
        <p className="mt-4 text-sm text-foreground/60">
          Sign-in is not configured on this installation, so Sarce runs in single-user mode.
        </p>
      ) : (
        <form className="mt-6 space-y-3" onSubmit={handleSubmit}>
          <label className="block text-sm text-foreground/70" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            disabled={busy}
            className="w-full rounded-lg border border-white/10 bg-background px-4 py-2 text-sm outline-none focus:border-accent/50"
          />
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-background transition hover:bg-accent/90 disabled:opacity-50"
          >
            {busy ? "Sending..." : "Email me a sign-in link"}
          </button>
          {status && <p className="text-sm text-foreground/70">{status}</p>}
        </form>
      )}

      <Link href="/" className="mt-6 text-sm text-foreground/50 hover:text-foreground/80">
        Back to the dashboard
      </Link>
    </main>
  );
}
