/**
 * Opponent prep (as on the web, apps/web/src/components/prep/prep-view.tsx): a private summary of a
 * player's recent finished games. Only usernames you type, finished games only, their games are not
 * kept, and every report can be deleted.
 */
import { useState } from "react";
import { TextInput, View } from "react-native";
import { Card, Choice, Label, Link, Loading, Primary, Screen, T, s } from "@/components/ui";
import { createReport, deleteReport, listReports } from "@/lib/api";
import { color, font } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

const MOTIFS: Record<string, string> = {
  sacrifice: "Sacrifices",
  fork: "Forks",
  pin: "Pins",
  skewer: "Skewers",
  discovered_attack: "Discovered attacks",
  hanging_piece: "Pieces left loose",
};

export default function Prep() {
  const { data, setData } = useLoad(listReports);
  const [site, setSite] = useState<"chess_com" | "lichess">("chess_com");
  const [username, setUsername] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  async function build() {
    const name = username.trim();
    if (!name || busy) return;
    setBusy(true);
    setStatus(null);
    try {
      const report = await createReport(name, site);
      setData({ reports: [report, ...(data?.reports ?? []).filter((r) => r.id !== report.id)] });
      setUsername("");
    } catch {
      setStatus("The report couldn't be built. Check the username and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen title="prep" back>
      <T weight="medium" size={22}>Opponent prep</T>
      <T mono size={11} tone="muted">finished games only · private · delete any time</T>
      <Card lead>
        <Label accent>Who are you playing?</Label>
        <View style={{ flexDirection: "row", gap: 6 }}>
          <View style={{ flex: 1 }}><Choice label="Chess.com" selected={site === "chess_com"} onPress={() => setSite("chess_com")} /></View>
          <View style={{ flex: 1 }}><Choice label="Lichess" selected={site === "lichess"} onPress={() => setSite("lichess")} /></View>
        </View>
        <TextInput
          value={username}
          onChangeText={setUsername}
          placeholder="Their username"
          placeholderTextColor={color.faint}
          autoCapitalize="none"
          autoCorrect={false}
          style={{ height: 44, borderWidth: 1.5, borderColor: color.line2, borderRadius: 6, paddingHorizontal: 12, fontFamily: font.sans, fontSize: 14, color: color.ink }}
        />
        <Primary label={busy ? "Reading their games…" : "Build report"} disabled={busy || !username.trim()} onPress={build} />
        {status && <T size={12} tone="muted">{status}</T>}
      </Card>
      {!data ? (
        <Loading />
      ) : data.reports.length === 0 ? (
        <T size={13} tone="muted">No reports yet.</T>
      ) : (
        data.reports.map((r) => (
          <Card key={r.id}>
            <View style={s.row}>
              <T weight="medium" size={16} style={{ flex: 1 }}>{r.username}</T>
              <Link
                label="Delete"
                tone="muted"
                onPress={() => {
                  deleteReport(r.id).catch(() => null);
                  setData({ reports: data.reports.filter((x) => x.id !== r.id) });
                }}
              />
            </View>
            <T mono size={11} tone="muted">{`${r.source === "lichess" ? "Lichess" : "Chess.com"} · ${r.gamesSampled} finished games`}</T>
            <Label>As White</Label>
            <T size={13} tone="ink2">{r.report.openingsAsWhite.slice(0, 3).map((o) => `${o.name} (${o.games})`).join(" · ") || "Not enough games"}</T>
            <Label>As Black</Label>
            <T size={13} tone="ink2">{r.report.openingsAsBlack.slice(0, 3).map((o) => `${o.name} (${o.games})`).join(" · ") || "Not enough games"}</T>
            <Label>Rough tendencies · per 100 moves</Label>
            <T size={13} tone="ink2">
              {Object.entries(r.report.motifsPer100Moves)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 3)
                .map(([k, v]) => `${MOTIFS[k] ?? k}: ${v}`)
                .join(" · ")}
            </T>
          </Card>
        ))
      )}
    </Screen>
  );
}
