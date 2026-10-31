"use client";

import Link from "next/link";
import { SarceMark } from "@/components/ui/icons";
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
      options: { emailRedirectTo: `${window.location.origin}/pilot` },
    });
    setStatus(error ? error.message : "Check your email for the sign-in link.");
    setBusy(false);
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-1 px-6">
      <SarceMark height={28} />
      <h1 className="mt-3 text-[22px] font-medium">Sign in to Sarce</h1>

      {!authConfigured() ? (
        <p className="mt-3 text-[13px] leading-[1.5] text-ink-2">
          Sign-in is not configured on this installation, so Sarce runs in single-user mode.
        </p>
      ) : (
        <form className="mt-6 space-y-3" onSubmit={handleSubmit}>
          <label className="block text-[13px] font-medium" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            disabled={busy}
            className="h-11 w-full rounded-[6px] border-[1.5px] border-line-2 bg-surface px-3 text-[14px]"
          />
          <button
            type="submit"
            disabled={busy}
            className="h-11 w-full rounded-[6px] bg-accent px-4 text-[14px] font-medium text-white transition-colors duration-[120ms] ease-sarce hover:bg-accent-hover active:bg-accent-active disabled:opacity-50"
          >
            {busy ? "Sending..." : "Email me a sign-in link"}
          </button>
          {status && <p className="text-[13px] text-ink-2">{status}</p>}
        </form>
      )}

      <Link href="/" className="mt-6 text-[13px] font-medium text-accent-text">
        Back to Home
      </Link>
    </main>
  );
}
