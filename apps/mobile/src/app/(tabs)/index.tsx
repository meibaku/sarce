/** Home (handoff screen 2): the latest game read in style terms, then Brilliant against your band. */
import { router } from "expo-router";
import { View } from "react-native";
import { Badge, Card, ChaosStrip, Edge, Gauge, Label, Link, Loading, Primary, Screen, T, Uncalibrated, s } from "@/components/ui";
import { Mascot } from "@/components/mascot";
import { getHome } from "@/lib/api";
import { useLoad } from "@/lib/use-load";

const RESULT = { win: "Won", loss: "Lost", draw: "Drew" } as const;

function Stat({ label, value }: { label: string; value: string | number | null }) {
  return (
    <View style={{ flex: 1, gap: 2 }}>
      <T mono weight="medium" size={16} tone={value == null ? "faint" : "ink"}>{value == null ? "—" : String(value)}</T>
      <T size={11} tone="muted">{label}</T>
    </View>
  );
}

export default function Home() {
  const { data, failed, reload } = useLoad(getHome);
  return (
    <Screen title="home">
      {failed ? (
        <Edge kind="offline" action="Try again" onAction={reload} />
      ) : !data ? (
        <Loading />
      ) : !data.latest ? (
        <Edge kind="no-games" action="Connect an account" onAction={() => router.push("/onboarding")} />
      ) : (
        <>
          <Card lead>
            <View style={s.row}>
              <Label accent>Latest game</Label>
              <T mono size={11} tone="muted" style={{ flex: 1 }} numberOfLines={1}>
                {`${data.latest.result ? RESULT[data.latest.result] : "Played"} vs ${data.latest.opponent ?? "opponent"}${data.latest.timeControl ? ` · ${data.latest.timeControl}` : ""}`}
              </T>
              {!data.latest.calibrated && <Uncalibrated />}
            </View>
            <View style={[s.row, { alignItems: "flex-start" }]}>
              <T weight="medium" size={18} style={{ flex: 1 }}>{data.latest.styleRead}</T>
              <Mascot state="idle" size={40} />
            </View>
            {data.latest.chaos.length > 0 && <ChaosStrip chaos={data.latest.chaos} highlight={data.latest.highlight} />}
            {data.latest.moments.map((m) => (
              <View key={m.ply} style={s.row}>
                <Badge glyph={m.glyph} />
                <T size={13} tone="ink2" style={{ flex: 1 }}>{m.line}</T>
              </View>
            ))}
            <View style={[s.row, { gap: 18 }]}>
              <Primary
                label={data.latest.moments.length === 1 ? "See the moment" : `See the ${data.latest.moments.length} moments`}
                onPress={() => router.push(`/games/${data.latest!.gameId}`)}
              />
              <Link label="Full review" onPress={() => router.push(`/games/${data.latest!.gameId}/review`)} />
            </View>
          </Card>

          <Card>
            <Label>{`Brilliant · last ${data.brilliant.games}`}</Label>
            <T mono weight="medium" size={30} tone={data.brilliant.pct == null ? "faint" : "accentText"}>
              {data.brilliant.pct == null ? "—" : `${data.brilliant.pct.toFixed(1)}%`}
            </T>
            <Gauge value={data.brilliant.pct} lo={data.brilliant.goalLo} hi={data.brilliant.goalHi} />
            {data.brilliant.gapLine && <T size={13} tone="ink2">{data.brilliant.gapLine}</T>}
            {data.stats && (
              <View style={[s.row, { marginTop: 4 }]}>
                <Stat label="style streak" value={data.stats.streak == null ? null : `${data.stats.streak} game${data.stats.streak === 1 ? "" : "s"}`} />
                <Stat label="sound : unsound" value={data.stats.soundRatio == null ? null : `${data.stats.soundRatio.toFixed(1)} : 1`} />
                <Stat label="traps survived" value={data.stats.trapsSurvived == null ? null : `${Math.round(data.stats.trapsSurvived * 100)}%`} />
              </View>
            )}
          </Card>

          <View style={{ flexDirection: "row", gap: 12 }}>
            <Card style={{ flex: 1 }}>
              <Label>This week</Label>
              <Link label="Weekly recap" onPress={() => router.push("/recap")} />
            </Card>
            <Card style={{ flex: 1 }}>
              <Label>Your sacrifices</Label>
              <Link label="Open the library" onPress={() => router.push("/library")} />
            </Card>
          </View>
        </>
      )}
    </Screen>
  );
}
