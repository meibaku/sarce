/**
 * Weekly recap (handoff screen 7, as the web's components/recap/recap-view.tsx): the streak, one bar per game of
 * the week (accent when it felt like you), Brilliant, best moment and last focus, then next week's focus.
 */
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, View } from "react-native";
import { SarceMark } from "@/components/icons";
import { Choice, Edge, Label, Link, Loading, Primary, Screen, T } from "@/components/ui";
import { getRecap, setFocus } from "@/lib/api";
import { color } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

const ORDINAL = ["", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"];

export default function Recap() {
  const { data, failed, reload } = useLoad(getRecap);
  const [focus, setChoice] = useState<string | null>(null);
  if (failed || !data) return <Screen title="weekly recap" back>{failed ? <Edge kind="offline" action="Try again" onAction={reload} /> : <Loading />}</Screen>;
  const chosen = focus ?? data.lastFocus?.id ?? data.focuses[0]?.id ?? null;
  const b = data.brilliant;
  const streak =
    data.streakWeeks > 1
      ? `Style streak kept for a ${ORDINAL[data.streakWeeks] ?? `${data.streakWeeks}th`} week.`
      : data.streakWeeks === 1
        ? "A week that counted toward your style."
        : "A quieter week for your style. That happens.";
  const rooks = Math.max(1, Math.min(3, data.streakWeeks));
  const box = { flex: 1, gap: 3, borderWidth: 1, borderColor: color.line, borderRadius: 6, backgroundColor: color.surface, padding: 12 } as const;

  return (
    <Screen title="weekly recap" back>
      <T mono size={11} tone="muted">{`Weekly recap · ${data.week}`}</T>
      <T weight="medium" size={26}>{`${data.games} game${data.games === 1 ? "" : "s"}, ${data.feltLikeYou} that felt like you`}</T>

      {/* One still rook per week of the streak (the web plays the streak skit when skits are on). */}
      <View style={{ flexDirection: "row", alignItems: "center", gap: 16, borderWidth: 1, borderColor: color.line, borderRadius: 8, backgroundColor: color.surface, paddingLeft: 8, paddingRight: 16, paddingTop: 8 }}>
        <View style={{ flexDirection: "row", alignItems: "flex-end", justifyContent: "center", gap: 12, height: 112, width: 170, borderBottomWidth: 1, borderColor: color.line2, paddingBottom: 4 }}>
          {Array.from({ length: rooks }, (_, i) => (
            <SarceMark key={i} height={i === rooks - 1 ? 64 : 52} color={color.ink} />
          ))}
        </View>
        <T size={14} tone="ink2" style={{ flex: 1, paddingBottom: 8 }}>{streak}</T>
      </View>

      <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 4, height: 72, borderBottomWidth: 1.5, borderColor: color.ink, paddingBottom: 4 }} accessibilityLabel="This week's games by style read">
        {data.bars.map((bar) => (
          <Pressable key={bar.gameId} accessibilityRole="link" accessibilityLabel={`Game, style read ${bar.styleRead}%`} onPress={() => router.push(`/games/${bar.gameId}`)} style={{ flex: 1, height: "100%", justifyContent: "flex-end" }}>
            <View style={{ height: `${Math.max(8, bar.styleRead)}%`, backgroundColor: bar.you ? color.accent : color.line3, borderTopLeftRadius: 2, borderTopRightRadius: 2 }} />
          </Pressable>
        ))}
      </View>

      <View style={{ flexDirection: "row", alignItems: "baseline", gap: 8 }}>
        <Label>Brilliant</Label>
        <T mono size={20} tone={b.pct == null ? "faint" : "accentText"}>{b.pct == null ? "—" : `${b.pct.toFixed(1)}%`}</T>
        <T mono size={11} tone="faint">
          {b.pct == null
            ? `${b.games} game${b.games === 1 ? "" : "s"} this week · needs 5`
            : [
                b.lo != null && b.hi != null ? `likely ${b.lo.toFixed(1)}–${b.hi.toFixed(1)}%` : b.spread != null ? `±${b.spread.toFixed(1)}` : null,
                // Up or down only when the weeks' ranges separate (review F4).
                b.change != null ? (b.trend ? `${b.trend} ${Math.abs(b.change).toFixed(1)}` : "about the same as last week") : null,
              ].filter(Boolean).join(" · ")}
        </T>
      </View>

      <View style={{ flexDirection: "row", gap: 10 }}>
        <View style={box}>
          <T mono size={10} tone="muted">best moment</T>
          {data.best ? (
            <Pressable accessibilityRole="link" onPress={() => router.push(`/games/${data.best?.gameId}/review`)}>
              <T mono weight="medium" size={14}>{data.best.label}</T>
            </Pressable>
          ) : (
            <T size={13} tone="muted">None this week</T>
          )}
        </View>
        <View style={box}>
          <T mono size={10} tone="muted">last focus</T>
          <T size={13}>{data.lastFocus?.line ?? data.lastFocus?.label ?? "None set yet"}</T>
          {data.questLine && <T size={12} tone="muted">{data.questLine}</T>}
        </View>
      </View>

      <T weight="medium" size={16} style={{ marginTop: 4 }}>Pick next week&apos;s focus</T>
      <View style={{ gap: 16 }}>
        {data.focuses.map((f) => (
          <Choice key={f.id} label={f.label} selected={chosen === f.id} onPress={() => setChoice(f.id)} />
        ))}
      </View>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
        <Primary label="Set focus · start Train" disabled={!chosen} onPress={() => chosen && setFocus("weekly", chosen).then(() => router.push("/train")).catch(() => null)} />
        <Link label="Keep last week's" tone="muted" onPress={() => router.back()} />
      </View>
    </Screen>
  );
}
