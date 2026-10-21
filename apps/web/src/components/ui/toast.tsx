"use client";

import { useEffect, useState } from "react";
import { Mascot } from "@/components/ui/mascot";

/*
 * Toasts (handoff motion table): a short confirmation with a mascot move, for 2.8s. Fired with
 * showToast() from anywhere; <Toaster> in the app shell renders the current one.
 */

type Toast = { id: number; message: string; move: string };

let listeners: ((t: Toast) => void)[] = [];
let next = 0;

/** e.g. showToast("Note saved.", "nod"). Moves: nod, hop, proud, think, shy, sleep, stretch. */
export function showToast(message: string, move = "nod") {
  const toast = { id: ++next, message, move };
  listeners.forEach((l) => l(toast));
}

export function Toaster() {
  const [toast, setToast] = useState<Toast | null>(null);

  useEffect(() => {
    const listen = (t: Toast) => setToast(t);
    listeners.push(listen);
    return () => {
      listeners = listeners.filter((l) => l !== listen);
    };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast((t) => (t?.id === toast.id ? null : t)), 2800);
    return () => clearTimeout(id);
  }, [toast]);

  if (!toast) return null;
  return (
    <div
      role="status"
      className="fixed right-4 bottom-[96px] z-40 flex max-w-[min(320px,calc(100%-32px))] items-center gap-3 rounded-[8px] border-[1.5px] border-ink bg-surface py-2 pr-4 pl-[10px] md:bottom-6"
      style={{ boxShadow: "0 6px 20px rgba(26,31,38,.08)" }}
    >
      <Mascot state={toast.move} size={40} />
      <span className="text-[13px] leading-[1.4]">{toast.message}</span>
    </div>
  );
}
