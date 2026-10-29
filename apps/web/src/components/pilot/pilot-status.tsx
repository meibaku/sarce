"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { getPilotPublicConfig, getPilotStatus, type PilotStatus } from "@/lib/api";

interface PilotStatusContextValue {
  status: PilotStatus | null;
  loading: boolean;
  offline: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const PilotStatusContext = createContext<PilotStatusContextValue | null>(null);

export function PilotStatusProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<PilotStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const config = await getPilotPublicConfig();
      if (config.mode !== "style_v1") {
        setStatus({ ...config, invitationRedeemed: false, admitted: false, collectionActive: false, state: "invited", startsAt: null, endsAt: null, targetReads: 10, completedReads: 0, answers: { yes: 0, partly: 0, no: 0 }, withdrawnAt: null, consent: null });
      } else {
        setStatus(await getPilotStatus());
      }
      setError(null);
    } catch {
      setError(`PILOT-${Date.now().toString(36).toUpperCase()}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const updateNetwork = () => setOffline(!navigator.onLine);
    updateNetwork();
    window.addEventListener("online", updateNetwork);
    window.addEventListener("offline", updateNetwork);
    void refresh();
    return () => {
      window.removeEventListener("online", updateNetwork);
      window.removeEventListener("offline", updateNetwork);
    };
  }, [refresh]);

  const value = useMemo(
    () => ({ status, loading, offline, error, refresh }),
    [status, loading, offline, error, refresh],
  );
  return <PilotStatusContext.Provider value={value}>{children}</PilotStatusContext.Provider>;
}

export function usePilotStatus() {
  const context = useContext(PilotStatusContext);
  if (!context) throw new Error("usePilotStatus must be used within PilotStatusProvider");
  return context;
}

export function PilotPageSkeleton() {
  return (
    <main data-pilot-shell className="min-h-dvh bg-page px-5 py-20 text-ink" aria-busy="true" aria-label="Loading pilot">
      <div className="mx-auto max-w-[1120px] space-y-5">
        <div className="pilot-skeleton h-4 w-48 rounded" />
        <div className="pilot-skeleton h-10 w-72 max-w-full rounded" />
        <div className="grid gap-5 md:grid-cols-2">
          <div className="pilot-skeleton h-56 rounded-[8px]" />
          <div className="pilot-skeleton h-56 rounded-[8px]" />
        </div>
      </div>
    </main>
  );
}

export function PilotModePage({ normal, pilot }: { normal: ReactNode; pilot: ReactNode }) {
  const router = useRouter();
  const { status, loading, error, refresh } = usePilotStatus();
  useEffect(() => {
    if (!loading && !status && !error) router.replace("/login");
    else if (!loading && status?.mode === "style_v1" && !status.admitted) router.replace("/pilot");
  }, [error, loading, router, status]);
  if (!loading && !status && error) return (
    <main data-pilot-shell className="grid min-h-dvh place-items-center bg-page px-5 text-ink" role="alert">
      <div className="max-w-md space-y-4 text-center">
        <h1 className="pilot-serif text-[30px]">Sarce could not open this page</h1>
        <p className="leading-6 text-ink-2">Your data has not changed. Check your connection and retry. Reference {error}.</p>
        <button type="button" onClick={() => void refresh()} className="min-h-11 rounded-[6px] bg-ink px-5 font-medium text-surface">Retry</button>
      </div>
    </main>
  );
  if (loading || !status || (status.mode === "style_v1" && !status.admitted)) return <PilotPageSkeleton />;
  return status.mode === "style_v1" ? pilot : normal;
}
