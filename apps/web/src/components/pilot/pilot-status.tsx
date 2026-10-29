"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getPilotStatus, type PilotStatus } from "@/lib/api";

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
      setStatus(await getPilotStatus());
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
      <div className="mx-auto max-w-[1080px] space-y-5">
        <div className="pilot-skeleton h-4 w-48 rounded" />
        <div className="pilot-skeleton h-10 w-72 max-w-full rounded" />
        <div className="grid gap-5 md:grid-cols-2">
          <div className="pilot-skeleton h-56 rounded-[10px]" />
          <div className="pilot-skeleton h-56 rounded-[10px]" />
        </div>
      </div>
    </main>
  );
}
