/** Weekly recap (handoff screen 7): the week's games in style terms, then choose next week's focus. */
import { router } from "expo-router";
import { useState } from "react";
import { View } from "react-native";
import { Card, Choice, Edge, Label, Link, Loading, Primary, Screen, T } from "@/components/ui";
import { getRecap, setFocus } from "@/lib/api";
import { color } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

export default function Recap() {
  const { data, failed, reload } = useLoad(getRecap);
  const [focus, setChoice] = useState<string | null>(null);
  if (failed || !data) return <Screen title="recap" back>{failed ? <Edge kind="offline" action="Try again" onAction={reload} /> : <Loading />}</Screen>;
  return (
    <Screen title="recap" back>
      <T mono size={11} tone="muted">{data.week}</T>
      <T weight="medium" size={22}>{`${data.games} games · ${data.feltLikeYou} felt like you`}</T>
      <Card>
        <Label>Style read per game</Label>
        <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 4, height: 64 }}>
          {data.bars.map((b) => (
            <View key={b.gameId} style={{ flex: 1, height: Math.max(3, (b.styleRead / 100) * 64), backgroundColor: b.you ? color.accent : color.line3, borderRadius: 2 }} />
          ))}
        </View>
        <T size={13} tone="ink2">
          {data.brilliant.pct == null ? "Brilliant fills in after five analysed games." : `Brilliant ${data.brilliant.pct.toFixed(1)}%${data.brilliant.change != null ? ` · ${data.brilliant.change >= 0 ? "+" : ""}${data.brilliant.change.toFixed(1)} on last week` : ""}`}
        </T>
      </Card>
      {data.best && (
        <Card>
          <Label>Best moment</Label>
          <T weight="medium" size={15}>{data.best.label}</T>
          <Link label="Open in Review" onPress={() => router.push(`/games/${data.best?.gameId}/review`)} />
        </Card>
      )}
      {data.lastFocus?.label && (
        <Card>
          <Label>Last week&apos;s focus</Label>
          <T size={14}>{data.lastFocus.label}</T>
          {data.lastFocus.line && <T size={13} tone="ink2">{data.lastFocus.line}</T>}
        </Card>
      )}
      <Card lead>
        <Label accent>Next week, focus on</Label>
        {data.focuses.map((f) => (
          <Choice key={f.id} label={f.label} selected={focus === f.id} onPress={() => setChoice(f.id)} />
        ))}
      </Card>
      <Primary
        label="Set focus · start Train"
        disabled={!focus}
        onPress={() => focus && setFocus("weekly", focus).then(() => router.push("/train")).catch(() => null)}
      />
    </Screen>
  );
}
