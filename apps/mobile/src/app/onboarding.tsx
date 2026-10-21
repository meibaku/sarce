/**
 * Onboarding (handoff screen 1, as the web's components/onboarding/onboarding-flow.tsx): 1 connect (username only,
 * no password) → 2 a real moment from the last game, before any setup → 3 the style goal → 4 the one-question rule
 * and where the data lives.
 */
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, TextInput, View } from "react-native";
import type { HomeMoment } from "@sarce/types";
import { Badge, Choice, Link, Primary, Screen, T, s } from "@/components/ui";
import { Mascot, type MascotState } from "@/components/mascot";
import { getHome, importGames, updateSettings } from "@/lib/api";
import { moveLabel } from "@/lib/format";
import { color, font } from "@/lib/theme";

const GOALS: { id: string; title: string; detail: string; lo: number; hi: number }[] = [
  { id: "tal", title: "More Tal", detail: "Sacrifices and initiative · band 6–10%", lo: 6, hi: 10 },
  { id: "solid", title: "More solid", detail: "Safer replies, fewer risks · band 2–4%", lo: 2, hi: 4 },
  { id: "none", title: "No goal yet", detail: "Sarce just mirrors your games for now", lo: 0, hi: 15 },
];

const STEPS = ["Connect", "First moment", "Style goal", "One question"];
const MOODS: MascotState[] = ["hello", "curious", "think", "proud"];

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const [site, setSite] = useState<"chess_com" | "lichess">("chess_com");
  const [username, setUsername] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [moment, setMoment] = useState<(HomeMoment & { opponent: string | null }) | null>(null);
  const [goal, setGoal] = useState("tal");

  useEffect(() => {
    if (step !== 1) return;
    getHome()
      .then((h) => {
        const m = h.latest?.moments[0];
        setMoment(m ? { ...m, opponent: h.latest?.opponent ?? null } : null);
      })
      .catch(() => setMoment(null));
  }, [step]);

  async function next() {
    if (step === 0) {
      const name = username.trim();
      if (!name) {
        setStatus("Enter your username first.");
        return;
      }
      setBusy(true);
      setStatus(null);
      try {
        const res = await importGames(site, name);
        // Saved so new games keep arriving by themselves (automatic sync).
        await updateSettings(site === "lichess" ? { lichessUsername: name } : { chessComUsername: name }).catch(() => undefined);
        setStatus(`Found ${res.imported} finished games. Analysis has started.`);
        setStep(1);
      } catch {
        setStatus("That username couldn't be imported. Check it, and that the analysis service is running.");
      } finally {
        setBusy(false);
      }
      return;
    }
    if (step === 2) {
      const g = GOALS.find((x) => x.id === goal) ?? GOALS[0];
      await updateSettings({ goalLo: g.lo, goalHi: g.hi, sources: site }).catch(() => undefined);
    }
    if (step === 3) {
      router.replace("/");
      return;
    }
    setStep(step + 1);
  }

  return (
    <Screen title="welcome" back>
      <Mascot state={MOODS[step]} size={64} />
      <View style={{ flexDirection: "row", gap: 6 }}>
        {STEPS.map((label, i) => (
          <View key={label} style={{ flex: 1, height: 3, borderRadius: 2, backgroundColor: i <= step ? color.ink : color.line }} />
        ))}
      </View>
      <T mono size={11} tone="muted">{`Step ${step + 1} of 4 · ${STEPS[step]}`}</T>

      {step === 0 && (
        <>
          <T weight="medium" size={26}>Connect where you play</T>
          <T size={14} tone="muted">Username only, no password. Sarce reads finished games, never live ones.</T>
          <View style={{ gap: 8 }}>
            <Choice label="Chess.com" selected={site === "chess_com"} onPress={() => setSite("chess_com")} />
            <Choice label="Lichess" selected={site === "lichess"} onPress={() => setSite("lichess")} />
            <TextInput
              value={username}
              onChangeText={setUsername}
              onSubmitEditing={next}
              placeholder={site === "lichess" ? "your Lichess username" : "your Chess.com username"}
              placeholderTextColor={color.faint}
              accessibilityLabel="Username"
              autoCapitalize="none"
              autoCorrect={false}
              style={{ height: 44, borderWidth: 1.5, borderColor: color.line2, borderRadius: 6, paddingHorizontal: 14, fontFamily: font.sans, fontSize: 13, color: color.ink, backgroundColor: color.surface }}
            />
          </View>
        </>
      )}

      {step === 1 && (
        <>
          <T weight="medium" size={26}>Here&apos;s a moment from your last game</T>
          <T size={14} tone="muted">Value before setup: this is what Sarce does, before it asks you anything.</T>
          {moment ? (
            <View style={[s.row, { gap: 12, borderWidth: 1.5, borderColor: color.ink, borderRadius: 8, backgroundColor: color.surface, padding: 14 }]}>
              <Badge glyph={moment.glyph} />
              <View style={{ flex: 1, gap: 2 }}>
                <T mono weight="medium" size={14}>{`${moveLabel(moment.ply, moment.san)} vs ${moment.opponent ?? "your opponent"}`}</T>
                <T size={13} tone="ink2">{moment.line}</T>
              </View>
            </View>
          ) : (
            <View style={{ borderWidth: 1.5, borderStyle: "dashed", borderColor: color.line3, borderRadius: 8, padding: 14 }}>
              <T size={13} tone="ink2">Your games are being read. The first moments appear on Home as soon as they&apos;re scored.</T>
            </View>
          )}
          <T mono size={11} tone="muted">More moments still being scored…</T>
        </>
      )}

      {step === 2 && (
        <>
          <T weight="medium" size={26}>Who are you trying to become?</T>
          <T size={14} tone="muted">Sarce measures distance from the style you pick, not from the engine.</T>
          <View style={{ gap: 16 }} accessibilityRole="radiogroup">
            {GOALS.map((g) => (
              <Pressable
                key={g.id}
                accessibilityRole="radio"
                accessibilityState={{ checked: goal === g.id }}
                onPress={() => setGoal(g.id)}
                style={{ flexDirection: "row", gap: 12, alignItems: "flex-start", borderWidth: 1.5, borderRadius: 8, paddingHorizontal: 16, paddingVertical: 14, borderColor: goal === g.id ? color.accent : color.line2, backgroundColor: goal === g.id ? color.accentTint : color.surface }}
              >
                <View style={{ marginTop: 2, width: 16, height: 16, borderRadius: 8, borderWidth: 1.5, borderColor: color.ink, alignItems: "center", justifyContent: "center" }}>
                  <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: goal === g.id ? color.accent : "transparent" }} />
                </View>
                <View style={{ flex: 1, gap: 3 }}>
                  <T weight="medium" size={15}>{g.title}</T>
                  <T size={13} tone="muted">{g.detail}</T>
                </View>
              </Pressable>
            ))}
          </View>
        </>
      )}

      {step === 3 && (
        <>
          <T weight="medium" size={26}>One question per game, at most</T>
          <T size={14} tone="muted">
            After some games Sarce asks one thing: did it feel like you, what you meant, or a random check-in that tests whether its flags mean
            anything. Skip any of them, any time.
          </T>
          <View style={{ borderRadius: 8, backgroundColor: color.panel, paddingHorizontal: 14, paddingVertical: 12 }}>
            <T size={13} tone="ink2">Your data stays on your own analysis service. Settings → What Sarce keeps.</T>
          </View>
        </>
      )}

      {status && <T size={13} tone="ink2">{status}</T>}
      <View style={[s.row, { gap: 18, marginTop: 8 }]}>
        <Primary label={busy ? "Connecting…" : step === 3 ? "Open Sarce" : "Continue"} disabled={busy} onPress={next} />
        <Link label="Back" tone="muted" onPress={() => (step > 0 ? setStep(step - 1) : router.back())} />
      </View>
    </Screen>
  );
}
