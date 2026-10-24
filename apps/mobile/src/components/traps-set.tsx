/**
 * Your traps on the phone (the web's components/you/traps-set.tsx): opening positions you steer into where opponents
 * most often go wrong on the very next move.
 */
import { useState } from "react";
import { Pressable, View } from "react-native";
import { Board } from "@/components/board";
import { Card, Label, Link, T, s } from "@/components/ui";
import { getTrapsSet, rebuildTrapsSet } from "@/lib/api";
import { color } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

const pct = (v: number) => `${Math.round(v * 100)}%`;

export function TrapsSetCard() {
  const { data, reload } = useLoad(getTrapsSet);
  const [pick, setPick] = useState(0);
  const [asked, setAsked] = useState(false);
  const traps = data?.traps ?? [];
  const t = traps[pick] ?? traps[0];
  const building = asked || data?.building;
  return (
    <Card>
      <View style={s.row}>
        <Label>Your traps · openings</Label>
        <View style={{ flex: 1 }} />
        <Link
          label={building ? "Reading your games…" : traps.length ? "Rebuild" : "Find my traps"}
          onPress={() => {
            if (building) return reload();
            setAsked(true);
            rebuildTrapsSet().catch(() => setAsked(false));
          }}
        />
      </View>
      {!t ? (
        <T size={13} tone="muted">{building ? "Under a minute, no engine needed. Tap again to check." : "Positions you steer into where opponents most often go wrong on the next move."}</T>
      ) : (
        <>
          <T weight="medium" size={15}>{`After ${t.move}, ${pct(t.rate)} of opponents went wrong (likely at least ${pct(t.likely)}).`}</T>
          <Board fen={t.fen} orientation={t.fen.split(" ")[1] === "b" ? "white" : "black"} maxSize={300} />
          <T size={12} tone="ink2">{`Caught ${t.caught} of ${t.seen}. The usual slip is ${t.slip}, worth about ${t.gainPawns.toFixed(1)} pawns. The defence that holds is ${t.defence}.`}</T>
          {traps.map((x, i) => (
            <Pressable
              key={x.fen}
              onPress={() => setPick(i)}
              style={{ flexDirection: "row", gap: 8, borderTopWidth: 1, borderColor: color.hair, paddingVertical: 8, backgroundColor: x === t ? color.accentTint : undefined }}
            >
              <View style={{ flex: 1 }}>
                <T mono size={12} numberOfLines={1}>{x.line}</T>
                <T size={12} tone="muted">{`caught ${x.caught} of ${x.seen} · they slip with ${x.slip}`}</T>
              </View>
              <T mono weight="medium" tone="accentText">{`≥${pct(x.likely)}`}</T>
            </Pressable>
          ))}
        </>
      )}
    </Card>
  );
}
