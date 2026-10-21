/** Sacrifice library (handoff screen 6): All / Held / Didn't hold, each row opens in Review. */
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { Pressable, View } from "react-native";
import { Badge, Choice, Edge, Loading, Screen, T, s } from "@/components/ui";
import { getSacrifices } from "@/lib/api";
import { color } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

type Filter = "all" | "held" | "not";

export default function Library() {
  const { data, failed, reload } = useLoad(getSacrifices);
  const [filter, setFilter] = useState<Filter>("all");
  const rows = useMemo(() => (data?.sacrifices ?? []).filter((r) => filter === "all" || (filter === "held" ? r.held : !r.held)), [data, filter]);
  return (
    <Screen title="library" back>
      <T weight="medium" size={22}>Your sacrifices</T>
      <T mono size={11} tone="muted">a living record · newest first</T>
      <View style={{ flexDirection: "row", gap: 6 }}>
        {(
          [
            ["all", `All ${data?.sacrifices.length ?? ""}`],
            ["held", "Held"],
            ["not", "Didn't hold"],
          ] as [Filter, string][]
        ).map(([v, label]) => (
          <Choice key={v} label={label} selected={filter === v} onPress={() => setFilter(v)} />
        ))}
      </View>
      {failed ? (
        <Edge kind="offline" action="Try again" onAction={reload} />
      ) : !data ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Edge kind="too-few" detail="No sacrifices here yet. They appear as your games are analysed." />
      ) : (
        <View style={{ borderWidth: 1, borderColor: color.line, borderRadius: 8, backgroundColor: color.surface, overflow: "hidden" }}>
          {rows.map((r, i) => (
            <Pressable
              key={`${r.gameId}-${r.ply}`}
              onPress={() => router.push(`/games/${r.gameId}/review`)}
              style={({ pressed }) => [s.row, { padding: 14, borderTopWidth: i ? 1 : 0, borderTopColor: color.hair, backgroundColor: pressed ? color.panel : color.surface }]}
            >
              <Badge glyph={r.glyph} />
              <View style={{ flex: 1, gap: 2 }}>
                <T mono weight="medium" size={13}>{`${r.label} · ${r.type} −${r.material}`}</T>
                <T size={12} tone="muted" numberOfLines={1}>{`vs ${r.opponent ?? "opponent"}${r.opening ? ` · ${r.opening}` : ""}`}</T>
              </View>
              <T size={12} tone={r.held ? "sound" : "muted"}>{r.held ? "Held" : "Didn't hold"}</T>
            </Pressable>
          ))}
        </View>
      )}
    </Screen>
  );
}
