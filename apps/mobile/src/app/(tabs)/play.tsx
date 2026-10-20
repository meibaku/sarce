/**
 * Play (handoff screen 9). Only against Sarce bots: nothing here runs during a game on another
 * site. Today's intention is saved for the next summary to grade, and never shown mid-game.
 */
import { router } from "expo-router";
import { useState } from "react";
import type { BotId } from "@sarce/types";
import { Card, Choice, Label, Primary, Screen, T } from "@/components/ui";
import { setFocus } from "@/lib/api";
import { BOTS, INTENTS } from "@/lib/play";

export default function Play() {
  const [intent, setIntent] = useState<string | null>(null);
  const [bot, setBot] = useState<BotId>("defender");
  const current = BOTS.find((b) => b.id === bot) ?? BOTS[0];
  return (
    <Screen title="play">
      <T weight="medium" size={22}>Play</T>
      <T mono size={11} tone="muted">vs Sarce bots only · nothing runs during games on other sites</T>
      <Card lead>
        <Label accent>Today I want to…</Label>
        {INTENTS.map(([id, label]) => (
          <Choice
            key={id}
            label={label}
            selected={intent === id}
            onPress={() => {
              setIntent(id);
              setFocus("today", id).catch(() => null);
            }}
          />
        ))}
        <T size={12} tone="muted">Graded after the game, never during it.</T>
      </Card>
      <Card>
        <Label>Opponent</Label>
        {BOTS.map((b) => (
          <Choice key={b.id} label={b.label} selected={bot === b.id} onPress={() => setBot(b.id)} />
        ))}
        <T size={13} tone="ink2">{`Why this bot: ${current.why}`}</T>
      </Card>
      <Primary label="Play 3+0" onPress={() => router.push({ pathname: "/play/game", params: { bot } })} />
    </Screen>
  );
}
