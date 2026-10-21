/**
 * Settings (handoff screen 10): style goal, question budget, quiet week, sources and accounts with
 * sync, and the plain-language model card. Every change is saved straight away.
 */
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, Share, Switch, TextInput, View } from "react-native";
import type { SettingsApi } from "@sarce/types";
import { Card, Choice, Edge, Gauge, Label, Link, Loading, Screen, T, s } from "@/components/ui";
import { API_BASE, getJournal, getSettings, getSync, syncNow, updateSettings } from "@/lib/api";
import { setPrefs } from "@/lib/prefs";
import { color, font } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

function Stepper({ value, onChange, min, max }: { value: number; onChange: (v: number) => void; min: number; max: number }) {
  const btn = (label: string, next: number) => (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label === "−" ? "Lower" : "Higher"}
      disabled={next < min || next > max}
      onPress={() => onChange(next)}
      hitSlop={4} // 36px drawn, 44px to the touch
      style={{ width: 36, height: 36, borderRadius: 6, borderWidth: 1.5, borderColor: color.line2, alignItems: "center", justifyContent: "center", opacity: next < min || next > max ? 0.4 : 1 }}
    >
      <T size={16}>{label}</T>
    </Pressable>
  );
  return (
    <View style={s.row}>
      {btn("−", value - 1)}
      <T mono size={20} tone="accentText" style={{ minWidth: 56, textAlign: "center" }}>{`${value}%`}</T>
      {btn("+", value + 1)}
    </View>
  );
}

const field = { height: 40, borderWidth: 1.5, borderColor: color.line2, borderRadius: 6, paddingHorizontal: 12, fontFamily: font.sans, fontSize: 13, color: color.ink } as const;

export default function Settings() {
  const { data, failed, reload, setData } = useLoad(getSettings);
  const sync = useLoad(getSync);
  const [note, setNote] = useState<string | null>(null);

  function change(changes: Partial<SettingsApi>) {
    if (!data) return;
    const previous = data;
    setData({ ...data, ...changes });
    updateSettings(changes)
      .then((saved) => {
        setData((d) => ({ ...saved, kept: d?.kept }));
        setPrefs(saved); // mascot, motion and quiet week follow at once, everywhere
      })
      .catch(() => {
      setData(previous);
      setNote("That change couldn't be saved.");
    });
  }

  if (failed || !data) return <Screen title="settings" back>{failed ? <Edge kind="offline" action="Try again" onAction={reload} /> : <Loading />}</Screen>;
  const quiet = Boolean(data.quietUntil);
  return (
    <Screen title="settings" back>
      <T weight="medium" size={22}>Settings</T>
      {note && <T size={12} tone="muted">{note}</T>}

      <Card lead>
        <Label accent>Style goal</Label>
        <T size={13} tone="ink2">Your target Brilliant band. Every gauge in the app follows it.</T>
        {(
          [
            ["from", data.goalLo, 0, data.goalHi - 1, "goalLo"],
            ["to", data.goalHi, data.goalLo + 1, 15, "goalHi"],
          ] as const
        ).map(([label, value, min, max, key]) => (
          <View key={label} style={[s.row, { gap: 12 }]}>
            <T size={13} tone="muted" style={{ width: 36 }}>{label}</T>
            <Stepper value={value} min={min} max={max} onChange={(v) => change({ [key]: v })} />
          </View>
        ))}
        <Gauge value={null} lo={data.goalLo} hi={data.goalHi} compact />
        <T mono size={11} tone="muted">references: Tal · change in You</T>
      </Card>

      <Card>
        <Label>Questions after a game</Label>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
          {([0, 1, 2] as const).map((n) => (
            <Choice key={n} label={["None", "One per game", "Up to two"][n]} selected={data.questionBudget === n} onPress={() => change({ questionBudget: n })} />
          ))}
        </View>
        <T size={12} tone="muted">Rotates between &quot;felt like you&quot;, intent and random check-ins. Notifications: after a game, quiet 23:00–08:00.</T>
        <View style={[s.row, { justifyContent: "space-between" }]}>
          <View style={{ flex: 1 }}>
            <T weight="medium" size={14}>Quiet week</T>
            <T size={12} tone="muted">{quiet ? `Numbers hidden until ${data.quietUntil}.` : "Hide every number for 7 days."}</T>
          </View>
          <Switch
            value={quiet}
            onValueChange={(on) => change({ quietUntil: on ? new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10) : null })}
            trackColor={{ true: color.accent, false: color.line2 }}
            thumbColor="#fff"
          />
        </View>
      </Card>

      <Card>
        <Label>Sources and theme</Label>
        <View style={{ flexDirection: "row", gap: 6 }}>
          {(
            [
              ["chess_com", "Chess.com"],
              ["lichess", "Lichess"],
              ["both", "Both"],
            ] as const
          ).map(([v, label]) => (
            <View key={v} style={{ flex: 1 }}>
              <Choice label={label} selected={data.sources === v} onPress={() => change({ sources: v })} />
            </View>
          ))}
        </View>
        <View style={{ flexDirection: "row", gap: 6 }}>
          {(
            [
              ["light", "Light"],
              ["system", "Match system"],
            ] as const
          ).map(([v, label]) => (
            <View key={v} style={{ flex: 1 }}>
              <Choice label={label} selected={(data.theme === "dark" ? "system" : data.theme) === v} onPress={() => change({ theme: v })} />
            </View>
          ))}
        </View>
        {/* The phone app draws light only so far (the web has dark); the handoff's own note says the same. */}
        <T size={12} tone="muted">Dark theme is planned for v1.1; &quot;Match system&quot; stays light until then.</T>
        {(
          [
            ["chessComUsername", "Chess.com username"],
            ["lichessUsername", "Lichess username"],
          ] as const
        ).map(([key, label]) => (
          <TextInput
            key={`${key}-${data[key] ?? ""}`}
            defaultValue={data[key] ?? ""}
            placeholder={label}
            placeholderTextColor={color.faint}
            accessibilityLabel={label}
            autoCapitalize="none"
            autoCorrect={false}
            onEndEditing={(e) => {
              const value = e.nativeEvent.text.trim() || null;
              if (value !== (data[key] ?? null)) change({ [key]: value });
            }}
            style={field}
          />
        ))}
        <View style={s.row}>
          <T mono size={11} tone="muted" style={{ flex: 1 }}>
            {sync.data ? `${sync.data.lastSyncedAt ? "synced" : "not synced yet"} · ${sync.data.pending + sync.data.processing} to analyse` : " "}
          </T>
          <Link label="Sync now" onPress={() => syncNow().then(() => setNote("Syncing. New games are analysed in the background.")).catch(() => setNote("Sync couldn't start."))} />
        </View>
      </Card>

      <Card>
        <Label>Mascot and motion</Label>
        <View style={[s.row, { justifyContent: "space-between" }]}>
          <View style={{ flex: 1 }}>
            <T weight="medium" size={14}>Playful mascot</T>
            <T size={12} tone="muted">Off shows the still mark: no eyes, no animation.</T>
          </View>
          <Switch value={data.playfulMascot} onValueChange={(on) => change({ playfulMascot: on })} trackColor={{ true: color.accent, false: color.line2 }} thumbColor="#fff" />
        </View>
        <View style={{ flexDirection: "row", gap: 6 }}>
          {(
            [
              ["system", "Follow system"],
              ["full", "Full"],
              ["reduced", "Reduced"],
            ] as const
          ).map(([v, label]) => (
            <View key={v} style={{ flex: 1 }}>
              <Choice label={label} selected={data.motion === v} onPress={() => change({ motion: v })} />
            </View>
          ))}
        </View>
      </Card>

      <Card>
        <Label>How Sarce reads your games</Label>
        <T size={13} tone="ink2">
          Stockfish 18 finds the best moves; a human model estimates how often players at your opponent&apos;s rating would miss the safe
          reply. Chaos numbers are validated on one-minute games only, so blitz and rapid say &quot;uncalibrated&quot;.
        </T>
        <T mono size={11} tone="muted">{`Analysis service · ${API_BASE}`}</T>
      </Card>

      <View style={[s.row, { gap: 18 }]}>
        <Link label="Replay onboarding" onPress={() => router.push("/onboarding")} />
        <Link
          label="Export journal"
          onPress={() =>
            getJournal()
              .then((text) => Share.share({ title: "Sarce journal", message: text }))
              .catch(() => setNote("The journal couldn't be exported."))
          }
        />
      </View>
    </Screen>
  );
}
