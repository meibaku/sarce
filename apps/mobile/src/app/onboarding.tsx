/**
 * Onboarding (handoff screen 1): connect a username (imports finished games and starts analysis),
 * choose the style goal, then the one-question rule. Local-first: nothing leaves your analysis service.
 */
import { router } from "expo-router";
import { useState } from "react";
import { TextInput, View } from "react-native";
import { Card, Choice, Label, Primary, Screen, T } from "@/components/ui";
import { Mascot } from "@/components/mascot";
import { importGames, updateSettings } from "@/lib/api";
import { color, font } from "@/lib/theme";

const GOALS: [number, number, string][] = [
  [3, 6, "Grounded · 3–6%"],
  [6, 10, "Tal-inspired · 6–10%"],
  [10, 15, "All in · 10–15%"],
];

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const [site, setSite] = useState<"chess_com" | "lichess">("chess_com");
  const [username, setUsername] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [goal, setGoal] = useState(1);

  async function connect() {
    const name = username.trim();
    if (!name) return;
    setBusy(true);
    setStatus(null);
    try {
      const res = await importGames(site, name);
      await updateSettings(site === "lichess" ? { lichessUsername: name } : { chessComUsername: name });
      setStatus(`Found ${res.imported} finished games. Analysis has started.`);
      setStep(1);
    } catch {
      setStatus("Couldn't import those games. Check the username and that the analysis service is running.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen title="welcome" back>
      <View style={{ flexDirection: "row", gap: 4 }}>
        {[0, 1, 2].map((i) => (
          <View key={i} style={{ flex: 1, height: 3, borderRadius: 2, backgroundColor: i <= step ? color.accent : color.line }} />
        ))}
      </View>
      <Mascot state={step === 0 ? "hello" : step === 1 ? "curious" : "proud"} size={56} />
      {step === 0 && (
        <Card lead>
          <Label accent>Step 1 of 3</Label>
          <T weight="medium" size={20}>Where do you play?</T>
          <View style={{ flexDirection: "row", gap: 6 }}>
            <View style={{ flex: 1 }}><Choice label="Chess.com" selected={site === "chess_com"} onPress={() => setSite("chess_com")} /></View>
            <View style={{ flex: 1 }}><Choice label="Lichess" selected={site === "lichess"} onPress={() => setSite("lichess")} /></View>
          </View>
          <TextInput
            value={username}
            onChangeText={setUsername}
            placeholder="Your username"
            placeholderTextColor={color.faint}
            autoCapitalize="none"
            autoCorrect={false}
            style={{ height: 44, borderWidth: 1.5, borderColor: color.line2, borderRadius: 6, paddingHorizontal: 12, fontFamily: font.sans, fontSize: 14, color: color.ink }}
          />
          <T size={12} tone="muted">Finished games only. Sarce never looks at a game in progress.</T>
          <Primary label={busy ? "Reading your games…" : "Connect"} disabled={busy || !username.trim()} onPress={connect} />
          {status && <T size={12} tone="ink2">{status}</T>}
        </Card>
      )}
      {step === 1 && (
        <Card lead>
          <Label accent>Step 2 of 3</Label>
          <T weight="medium" size={20}>How often do you want to be brilliant?</T>
          {status && <T size={12} tone="muted">{status}</T>}
          {GOALS.map(([, , label], i) => (
            <Choice key={label} label={label} selected={goal === i} onPress={() => setGoal(i)} />
          ))}
          <Primary
            label="Continue"
            onPress={() => {
              const [lo, hi] = GOALS[goal];
              updateSettings({ goalLo: lo, goalHi: hi }).catch(() => null);
              setStep(2);
            }}
          />
        </Card>
      )}
      {step === 2 && (
        <Card lead>
          <Label accent>Step 3 of 3</Label>
          <T weight="medium" size={20}>One question per game</T>
          <T size={13} tone="ink2">
            After a game Sarce asks at most one thing, like &quot;Did this game feel like you?&quot;. Your answers and notes stay on your own
            analysis service.
          </T>
          <Primary label="Go to Home" onPress={() => router.replace("/")} />
        </Card>
      )}
    </Screen>
  );
}
