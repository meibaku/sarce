/**
 * Settings (handoff screen 10): style goal, question budget, quiet week, sources and accounts with
 * sync, and the plain-language model card. Every change is saved straight away.
 */
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, Switch, TextInput, View } from "react-native";
import type { SettingsApi } from "@sarce/types";
import { Card, Choice, Edge, Gauge, Label, Link, Loading, Screen, T, s } from "@/components/ui";
import { API_BASE, getSettings, getSync, syncNow, updateSettings } from "@/lib/api";
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
      style={{ width: 36, height: 36, borderRadius: 6, borderWidth: 1.5, borderColor: color.line2, alignItems: "center", justifyContent: "center", opacity: next < min || next > max ? 0.4 : 1 }}
    >
      <T size={16}>{label}</T>
    </Pressable>
  );
  return (
    <View style={s.row}>
      {btn("−", value - 1)}
      <T mono weight="medium" size={16} style={{ width: 36, textAlign: "center" }}>{`${value}%`}</T>
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
        <View style={[s.row, { justifyContent: "space-between" }]}>
          <View style={{ gap: 4 }}>
            <T size={12} tone="muted">From</T>
            <Stepper value={data.goalLo} min={0} max={data.goalHi - 1} onChange={(v) => change({ goalLo: v })} />
          </View>
          <View style={{ gap: 4 }}>
            <T size={12} tone="muted">To</T>
            <Stepper value={data.goalHi} min={data.goalLo + 1} max={15} onChange={(v) => change({ goalHi: v })} />
          </View>
        </View>
        <Gauge value={null} lo={data.goalLo} hi={data.goalHi} />
        <T size={12} tone="muted">Every gauge in the app follows this band.</T>
      </Card>

      <Card>
        <Label>Questions after a game</Label>
        <View style={{ flexDirection: "row", gap: 6 }}>
          {([0, 1, 2] as const).map((n) => (
            <View key={n} style={{ flex: 1 }}>
              <Choice label={n === 0 ? "None" : String(n)} selected={data.questionBudget === n} onPress={() => change({ questionBudget: n })} />
            </View>
          ))}
        </View>
        <View style={[s.row, { justifyContent: "space-between" }]}>
          <View style={{ flex: 1 }}>
            <T weight="medium" size={14}>Quiet week</T>
            <T size={12} tone="muted">{quiet ? `Until ${data.quietUntil} · numbers hidden, moments stay.` : "Hide numbers for seven days."}</T>
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
        <Label>Sources</Label>
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
      </View>
    </Screen>
  );
}
