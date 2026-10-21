"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { BotGame } from "@/components/play/bot-game";
import { AppShell } from "@/components/shell/app-shell";
import type { BotId } from "@/types/chess";

function Game() {
  const raw = useSearchParams().get("bot");
  const bot: BotId = raw === "tal" || raw === "swindler" ? raw : "defender";
  return <BotGame bot={bot} />;
}

export default function BotGamePage() {
  return (
    <AppShell title="play">
      <Suspense>
        <Game />
      </Suspense>
    </AppShell>
  );
}
