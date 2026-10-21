/**
 * Play (handoff screen 9, as the web's components/play/play-view.tsx). Only against Sarce bots: nothing here runs
 * during a game on another site. Today's intention is saved for the next summary to grade, never shown mid-game.
 */
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, View } from "react-native";
import type { BotId } from "@sarce/types";
import { Card, Choice, Label, Link, Primary, Screen, T } from "@/components/ui";
import { getFocus, setFocus } from "@/lib/api";
import { BOTS, INTENTS } from "@/lib/play";
import { color } from "@/lib/theme";

export default function Play() {
  const [intent, setIntent] = useState<string | null>(null);
  const [bot, setBot] = useState<BotId>("defender");
  const current = BOTS.find((b) => b.id === bot) ?? BOTS[0];
  useEffect(() => {
    getFocus()
      .then((f) => setIntent((now) => now ?? f.today))
      .catch(() => null);
  }, []);
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
        <T size={12} tone="muted">Your next summary grades the game against this first. It&apos;s stored when you leave Sarce and never shown during a game.</T>
      </Card>
      <Card>
        <Label>Warm-up · 2 min · optional</Label>
        <T weight="medium" size={15}>Two positions from this week&apos;s focus</T>
        <T size={13} tone="ink2">One sacrifice you played, one trap at your band. Skippable every time.</T>
        <Link label="Start warm-up" onPress={() => router.push("/train")} />
      </Card>
      <Card>
        <Label>Sarce bot</Label>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }} accessibilityRole="radiogroup">
          {BOTS.map((b) => (
            <Pressable
              key={b.id}
              accessibilityRole="radio"
              accessibilityState={{ checked: bot === b.id }}
              onPress={() => setBot(b.id)}
              hitSlop={6}
              style={{ borderWidth: 1.5, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, borderColor: bot === b.id ? color.accent : color.line2, backgroundColor: bot === b.id ? color.accentTint : color.surface }}
            >
              <T weight="medium" size={12} tone={bot === b.id ? "accentText" : "ink"}>{b.label}</T>
            </Pressable>
          ))}
        </View>
        <T size={13} tone="ink2">{`Why this bot: ${current.why}`}</T>
        <View style={{ alignSelf: "flex-start" }}>
          <Primary label="Play 3+0" onPress={() => router.push({ pathname: "/play/game", params: { bot } })} />
        </View>
      </Card>
      <Card>
        <Label>Opponent prep · private</Label>
        <T weight="medium" size={15}>Playing someone you know?</T>
        <T size={13} tone="ink2">Their openings and tendencies from finished games only. Only you see it.</T>
        <Link label="Prep for an opponent" onPress={() => router.push("/prep")} />
      </Card>
    </Screen>
  );
}
