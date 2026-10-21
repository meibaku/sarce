/**
 * Sacrifice library (handoff screen 6, as the web's components/library/library-view.tsx): All / Held / Didn't hold,
 * a living record newest first. The selected sacrifice opens below with your note, Review and its defence drill.
 */
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { Pressable, View } from "react-native";
import { Badge, Edge, Link, Loading, Primary, Screen, T, s } from "@/components/ui";
import { getSacrifices } from "@/lib/api";
import { color } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

type Filter = "all" | "held" | "not";
const PAGE = 20; // a long history would push the detail card out of reach

const date = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "");

export default function Library() {
  const { data, failed, reload } = useLoad(getSacrifices);
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState(0);
  const [all, setAll] = useState(false);
  const rows = useMemo(() => (data?.sacrifices ?? []).filter((r) => filter === "all" || (filter === "held" ? r.held : !r.held)), [data, filter]);
  const shown = all ? rows : rows.slice(0, PAGE);
  const sel = rows[Math.min(selected, rows.length - 1)];
  return (
    <Screen title="your sacrifices" back>
      <View style={[s.row, { alignItems: "baseline", gap: 12 }]}>
        <Link label="← You" onPress={() => router.back()} />
        <T weight="medium" size={22}>Your sacrifices</T>
      </View>
      <T mono size={11} tone="muted">a living record · newest first</T>
      <View style={{ flexDirection: "row", gap: 6 }}>
        {(
          [
            ["all", `All ${data?.sacrifices.length ?? ""}`],
            ["held", "Held"],
            ["not", "Didn't hold"],
          ] as [Filter, string][]
        ).map(([v, label]) => (
          <Pressable
            key={v}
            accessibilityRole="button"
            accessibilityState={{ selected: filter === v }}
            hitSlop={6}
            onPress={() => {
              setFilter(v);
              setSelected(0);
            }}
            style={{ height: 32, justifyContent: "center", paddingHorizontal: 12, borderRadius: 6, borderWidth: 1.5, borderColor: filter === v ? color.accent : color.line2, backgroundColor: filter === v ? color.accentTint : color.surface }}
          >
            <T weight="medium" size={12} tone={filter === v ? "accentText" : "ink"}>{label}</T>
          </Pressable>
        ))}
      </View>
      {failed ? (
        <Edge kind="offline" action="Try again" onAction={reload} />
      ) : !data ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Edge kind="too-few" detail="No sacrifices here yet. They appear as your games are analysed." />
      ) : (
        <>
          <View style={{ borderWidth: 1, borderColor: color.line, borderRadius: 8, backgroundColor: color.surface, overflow: "hidden" }}>
            {shown.map((r, i) => (
              <Pressable
                key={`${r.gameId}-${r.ply}`}
                accessibilityRole="button"
                accessibilityState={{ selected: sel === r }}
                onPress={() => setSelected(i)}
                style={[s.row, { paddingHorizontal: 16, paddingVertical: 12, gap: 12, borderTopWidth: i ? 1 : 0, borderTopColor: color.hair, backgroundColor: sel === r ? color.accentTint : color.surface }]}
              >
                <Badge glyph={r.glyph} />
                <View style={{ flex: 1, gap: 2 }}>
                  <T numberOfLines={1}>
                    <T mono weight="medium" size={13}>{r.label}</T>
                    <T size={13} tone="muted">{`  · ${r.type} −${r.material}`}</T>
                  </T>
                  <T size={12} tone="muted" numberOfLines={1}>{`vs ${r.opponent ?? "opponent"} · ${date(r.playedAt)}`}</T>
                </View>
                <T size={12} tone="ink2">{r.held ? "Held" : "Didn't hold"}</T>
              </Pressable>
            ))}
          </View>
          {!all && rows.length > PAGE && <Link label={`Show all ${rows.length}`} onPress={() => setAll(true)} />}
          {sel && (
            <View style={{ gap: 10, borderWidth: 1.5, borderColor: color.ink, borderRadius: 8, backgroundColor: color.surface, paddingHorizontal: 18, paddingVertical: 16 }}>
              <View style={[s.row, { gap: 10 }]}>
                <Badge glyph={sel.glyph} />
                <T mono weight="medium" size={16}>{sel.label}</T>
                <View style={{ flex: 1 }} />
                <T mono size={11} tone="muted">{`vs ${sel.opponent ?? "opponent"}`}</T>
              </View>
              <T size={13} tone="ink2">{`${sel.held ? "Held · the engine found no refutation" : "Didn't hold · the engine found a way through"} · ${sel.type} −${sel.material}`}</T>
              <View style={{ gap: 3, borderRadius: 6, backgroundColor: color.panel, paddingHorizontal: 12, paddingVertical: 10 }}>
                <T mono size={10} tone="muted">YOUR NOTE</T>
                <T size={13}>{sel.note || "No note yet. Add one in Review."}</T>
              </View>
              <View style={[s.row, { gap: 18, flexWrap: "wrap" }]}>
                <Primary label="Open in Review" onPress={() => router.push(`/games/${sel.gameId}/review`)} />
                {/* Only a sacrifice that held has a defence drill ("play the other side", the reply after it). */}
                <Link
                  label="Defend it yourself"
                  onPress={() => router.push(sel.held ? { pathname: "/train", params: { drill: `defend:${sel.gameId}:${sel.ply + 1}` } } : "/train")}
                />
              </View>
            </View>
          )}
        </>
      )}
    </Screen>
  );
}
