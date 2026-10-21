/**
 * Your chaos map on the phone (the web's components/you/chaos-map.tsx): the opening positions you reach most,
 * and the one sound move in each that asks your opponents the most. Biggest gain over your usual move first.
 */
import { useState } from "react";
import { Pressable, View } from "react-native";
import { Board } from "@/components/board";
import { Card, Label, Link, T, s } from "@/components/ui";
import { getChaosMap, rebuildChaosMap, type ChaosMapPosition } from "@/lib/api";
import { color } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

const pct = (v: number | null) => (v == null ? "–" : `${Math.round(v * 100)}%`);
const gain = (p: ChaosMapPosition) => (p.same ? 0 : (p.chaos.problem ?? 0) - (p.usual.problem ?? 0));
const WORTH_IT = 0.02; // as on the web and in chaos_map.drill_items

export function ChaosMapCard() {
  const { data, reload } = useLoad(getChaosMap);
  const [pick, setPick] = useState(0);
  const [asked, setAsked] = useState(false);
  const positions = [...(data?.positions ?? [])].sort((a, b) => gain(b) - gain(a));
  const p = positions[pick] ?? positions[0];
  const building = asked || data?.building;
  return (
    <Card>
      <View style={s.row}>
        <Label>Your chaos map · openings</Label>
        <View style={{ flex: 1 }} />
        <Link
          label={building ? "Reading your games…" : positions.length ? "Rebuild" : "Build my map"}
          onPress={() => {
            if (building) return reload();
            setAsked(true);
            rebuildChaosMap().catch(() => setAsked(false));
          }}
        />
      </View>
      {!p ? (
        <T size={13} tone="muted">{building ? "A minute or two of engine work. Tap again to check." : "The positions you reach again and again, and the one sound move in each that sets the hardest problem."}</T>
      ) : (
        <>
          <T weight="medium" size={15}>
            {gain(p) < WORTH_IT ? `Your ${p.usual.san} asks about as much as anything here.` : `Try ${p.chaos.san} instead of ${p.usual.san}.`}
          </T>
          <Board fen={p.fen} orientation={p.fen.split(" ")[1] === "b" ? "black" : "white"} hot={[p.chaos.uci.slice(0, 2), p.chaos.uci.slice(2, 4)]} maxSize={300} />
          <T size={12} tone="ink2">
            {`After ${p.chaos.san}, a player near ${p.elo} misses every safe reply ${pct(p.chaos.pFail)} of the time (your ${p.usual.san}: ${pct(p.usual.pFail)}). Problem ${p.chaos.problem?.toFixed(2) ?? "–"} vs ${p.usual.problem?.toFixed(2) ?? "–"}.`}
          </T>
          {positions.map((q, i) => (
            <Pressable
              key={q.key}
              onPress={() => setPick(i)}
              style={{ flexDirection: "row", gap: 8, borderTopWidth: 1, borderColor: color.hair, paddingVertical: 8, backgroundColor: q === p ? color.accentTint : undefined }}
            >
              <View style={{ flex: 1 }}>
                <T mono size={12} numberOfLines={1}>{q.line}</T>
                <T size={12} tone="muted">{`reached ${q.seen}× · you play ${q.usual.san}`}</T>
              </View>
              <T mono weight="medium" tone={gain(q) < WORTH_IT ? "sound" : "accentText"}>{gain(q) < WORTH_IT ? `${q.usual.san} ✓` : q.chaos.san}</T>
            </Pressable>
          ))}
        </>
      )}
    </Card>
  );
}
