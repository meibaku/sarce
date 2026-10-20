/**
 * Native versions of the v1.0 primitives (apps/web/src/components/ui): one filled accent button
 * per screen, outlined choices, accent-text links, mono labels, no red and no shadows. Copy follows
 * the handoff's mapping (unsound, didn't hold, never Phase 1 mistake labels).
 */
import { router } from "expo-router";
import type { ReactNode } from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, Text, View, type StyleProp, type TextStyle, type ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Mascot, type MascotState } from "@/components/mascot";
import { color, font } from "@/lib/theme";

export function T({
  children,
  style,
  mono,
  weight = "regular",
  size = 14,
  tone = "ink",
  numberOfLines,
}: {
  children: ReactNode;
  style?: StyleProp<TextStyle>;
  mono?: boolean;
  weight?: "regular" | "medium" | "semibold";
  size?: number;
  tone?: keyof typeof color;
  numberOfLines?: number;
}) {
  const family = mono ? (weight === "regular" ? font.mono : font.monoMedium) : weight === "regular" ? font.sans : weight === "medium" ? font.medium : font.semibold;
  return (
    <Text numberOfLines={numberOfLines} style={[{ fontFamily: family, fontSize: size, color: color[tone], lineHeight: Math.round(size * 1.45) }, style]}>
      {children}
    </Text>
  );
}

/** A tab's or a stack screen's scrolling body with the phone header (mark + subtitle). */
export function Screen({ title, children, back }: { title: string; children: ReactNode; back?: boolean }) {
  return (
    <SafeAreaView edges={["top"]} style={s.safe}>
      <View style={s.header}>
        {back ? (
          <Pressable accessibilityRole="button" accessibilityLabel="Back" onPress={() => router.back()} hitSlop={12}>
            <T size={20} tone="accentText">‹</T>
          </Pressable>
        ) : (
          <Image source={require("../../assets/mark.png")} style={{ width: 18, height: 22 }} resizeMode="contain" accessibilityLabel="Sarce" />
        )}
        <T weight="semibold" size={16}>sarce</T>
        <T mono size={11} tone="muted" style={{ marginLeft: 4 }} numberOfLines={1}>
          {title}
        </T>
        <View style={{ flex: 1 }} />
        {!back && (
          <Pressable accessibilityRole="button" accessibilityLabel="Settings" onPress={() => router.push("/settings")} style={s.gear} hitSlop={6}>
            <T size={15} tone="ink2">⚙</T>
          </Pressable>
        )}
      </View>
      <ScrollView contentContainerStyle={s.body}>{children}</ScrollView>
    </SafeAreaView>
  );
}

export function Card({ children, lead, style }: { children: ReactNode; lead?: boolean; style?: StyleProp<ViewStyle> }) {
  return <View style={[s.card, lead && s.lead, style]}>{children}</View>;
}

export function Label({ children, accent }: { children: ReactNode; accent?: boolean }) {
  return (
    <T weight="semibold" size={11} tone={accent ? "accentText" : "muted"} style={{ letterSpacing: 0.9, textTransform: "uppercase" }}>
      {children}
    </T>
  );
}

export function Primary({ label, onPress, disabled }: { label: string; onPress: () => void; disabled?: boolean }) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [s.primary, { backgroundColor: pressed ? color.accentPress : color.accent, opacity: disabled ? 0.5 : 1 }]}
    >
      <T weight="medium" size={14} style={{ color: "#fff" }}>
        {label}
      </T>
    </Pressable>
  );
}

export function Choice({ label, selected, onPress }: { label: string; selected?: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ checked: !!selected }}
      onPress={onPress}
      style={({ pressed }) => [s.choice, selected ? s.choiceOn : pressed && { backgroundColor: color.panel }]}
    >
      <T weight="medium" size={13} tone={selected ? "accentText" : "ink"}>
        {label}
      </T>
    </Pressable>
  );
}

export function Link({ label, onPress, tone = "accentText" }: { label: string; onPress: () => void; tone?: keyof typeof color }) {
  return (
    <Pressable accessibilityRole="link" onPress={onPress} hitSlop={8}>
      <T weight="medium" size={13} tone={tone}>
        {label}
      </T>
    </Pressable>
  );
}

const GLYPH: Record<string, { tone: keyof typeof color; label: string }> = {
  "!!": { tone: "accent", label: "Brilliant" },
  "!?": { tone: "accentText", label: "Speculative" },
  "✓": { tone: "sound", label: "Safe reply" },
  "?!": { tone: "checkin", label: "Check-in" },
  "?": { tone: "muted", label: "Didn't hold" },
};

export function Badge({ glyph }: { glyph: string }) {
  const g = GLYPH[glyph] ?? GLYPH["?"];
  return (
    <View accessibilityLabel={g.label} style={[s.badge, { borderColor: color[g.tone] }]}>
      <T mono weight="medium" size={11} tone={g.tone}>
        {glyph}
      </T>
    </View>
  );
}

export function Uncalibrated() {
  return (
    <View style={[s.badge, { borderColor: color.line3, width: undefined, paddingHorizontal: 6 }]}>
      <T mono size={10} tone="muted">uncalibrated</T>
    </View>
  );
}

/** Brilliant % on the 0–15 scale with the goal band; dashed when it rests on fewer than five games. */
export function Gauge({ value, lo, hi, compact }: { value: number | null; lo: number; hi: number; compact?: boolean }) {
  const pct = (v: number) => `${(Math.max(0, Math.min(15, v)) / 15) * 100}%` as const;
  return (
    <View style={{ gap: 4 }}>
      <View style={[s.track, compact && { height: 8 }]}>
        <View style={[s.band, { left: pct(lo), width: `${((hi - lo) / 15) * 100}%` }]} />
        {value != null && <View style={[s.marker, { left: pct(value) }]} />}
      </View>
      {!compact && (
        <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
          <T mono size={10} tone="faint">0%</T>
          <T mono size={10} tone="accentText">{`${lo}–${hi}% your band`}</T>
          <T mono size={10} tone="faint">15%</T>
        </View>
      )}
    </View>
  );
}

/** Chaos per move as bars (34 at most); the brilliant move, if any, in accent. */
export function ChaosStrip({ chaos, highlight }: { chaos: number[]; highlight: number | null }) {
  const bars = chaos.slice(0, 34);
  const max = Math.max(0.01, ...bars);
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 2, height: 32 }} accessibilityLabel="Chaos per move">
      {bars.map((v, i) => (
        <View key={i} style={{ flex: 1, height: Math.max(2, (v / max) * 32), backgroundColor: i === highlight ? color.accent : color.line3, borderRadius: 1 }} />
      ))}
    </View>
  );
}

export function Loading() {
  return (
    <View style={{ paddingVertical: 32 }}>
      <ActivityIndicator color={color.accent} />
    </View>
  );
}

export type EdgeKind = "no-games" | "analysing" | "failed" | "too-few" | "offline";

const EDGE: Record<EdgeKind, { title: string; line: string; mascot: MascotState }> = {
  "no-games": { mascot: "empty", title: "No games yet", line: "Connect your Chess.com or Lichess username and Sarce reads your finished games." },
  analysing: { mascot: "ring", title: "Still analysing", line: "Your games are being scored. Moments appear as they're ready." },
  failed: { mascot: "error", title: "Analysis didn't finish", line: "Something went wrong reading this game. Try again in a moment." },
  "too-few": { mascot: "uncalibrated", title: "A few more games", line: "This fills in after five analysed games." },
  offline: { mascot: "offline", title: "Can't reach Sarce", line: "The analysis service isn't answering. Is it running, and is the app pointed at it?" },
};

export function Edge({ kind, action, onAction, detail }: { kind: EdgeKind; action?: string; onAction?: () => void; detail?: string }) {
  const e = EDGE[kind];
  return (
    <Card style={{ alignItems: "flex-start", gap: 8, paddingVertical: 24 }}>
      <Mascot state={e.mascot} size={56} />
      <T weight="medium" size={18}>{e.title}</T>
      <T size={13} tone="ink2">{detail ?? e.line}</T>
      {action && onAction && <Link label={action} onPress={onAction} />}
    </Card>
  );
}

export const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.page },
  header: { height: 52, flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 16, borderBottomWidth: 1, borderBottomColor: color.line, backgroundColor: color.surface },
  gear: { width: 32, height: 32, borderRadius: 6, borderWidth: 1.5, borderColor: color.line2, alignItems: "center", justifyContent: "center" },
  body: { padding: 16, gap: 12, paddingBottom: 32 },
  card: { backgroundColor: color.surface, borderWidth: 1, borderColor: color.line, borderRadius: 8, padding: 16, gap: 10 },
  lead: { borderWidth: 1.5, borderColor: color.ink },
  primary: { height: 44, borderRadius: 6, alignItems: "center", justifyContent: "center", paddingHorizontal: 18, alignSelf: "flex-start" },
  choice: { minHeight: 44, borderRadius: 6, borderWidth: 1.5, borderColor: color.line2, backgroundColor: color.surface, justifyContent: "center", paddingHorizontal: 14 },
  choiceOn: { borderColor: color.accent, backgroundColor: color.accentTint },
  badge: { minWidth: 26, height: 22, borderRadius: 4, borderWidth: 1.5, alignItems: "center", justifyContent: "center" },
  track: { height: 14, borderRadius: 3, backgroundColor: color.panel, borderWidth: 1, borderColor: color.line, overflow: "visible" },
  band: { position: "absolute", top: 0, bottom: 0, backgroundColor: color.accentTint, borderWidth: 1, borderColor: color.accent },
  marker: { position: "absolute", top: -4, bottom: -4, width: 3, marginLeft: -1.5, backgroundColor: color.ink, borderRadius: 1 },
  row: { flexDirection: "row", alignItems: "center", gap: 10 },
});
