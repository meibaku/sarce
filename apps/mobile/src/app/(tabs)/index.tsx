/** Home (handoff screen 2): the latest game read in style terms, then Brilliant against your band. */
import { router } from "expo-router";
import { View } from "react-native";
import { Card, ChaosStrip, Edge, Gauge, Label, Link, Loading, Primary, Screen, T, Uncalibrated, s } from "@/components/ui";
import { Mascot } from "@/components/mascot";
import { getHome } from "@/lib/api";
import { usePrefs } from "@/lib/prefs";
import { color } from "@/lib/theme";
import { gameMeta, timeAgo } from "@/lib/format";
import { useLoad } from "@/lib/use-load";


function Stat({ label, value }: { label: string; value: string | number | null }) {
  return (
    <View style={{ flex: 1, gap: 1 }}>
      {/* Handoff stats: a small mono label over a mono value. */}
      <T mono size={10} tone="muted">{label}</T>
      <T mono size={16} tone={value == null ? "faint" : "ink"}>{value == null ? "—" : String(value)}</T>
    </View>
  );
}

export default function Home() {
  const { data, failed, reload } = useLoad(getHome);
  const quiet = Boolean(usePrefs().quietUntil);
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
          {quiet && (
            <View style={[s.row, { borderWidth: 1.5, borderStyle: "dashed", borderColor: color.line3, borderRadius: 8, padding: 12 }]}>
              <T size={13} tone="ink2" style={{ flex: 1 }}>Quiet week · numbers are hidden, moments and notes stay.</T>
              <Link label="End early" onPress={() => router.push("/settings")} />
            </View>
          )}
          <Card lead>
            {/* Handoff: "Latest game · when", the game in a mono chip, the style read, then the chaos strip. */}
            <View style={[s.row, { alignItems: "flex-start" }]}>
              <View style={{ flex: 1, gap: 8 }}>
                <T mono size={11} tone="muted">{`Latest game · ${timeAgo(data.latest.playedAt)}`}</T>
                <View style={[s.row, { flexWrap: "wrap", gap: 6 }]}>
                  <View style={{ borderWidth: 1, borderColor: color.line2, borderRadius: 5, paddingHorizontal: 7 }}>
                    <T mono size={11} tone="muted">{gameMeta(data.latest)}</T>
                  </View>
                  {!data.latest.calibrated && <Uncalibrated />}
                </View>
              </View>
              <Mascot state={quiet ? "sleep" : "idle"} size={44} />
            </View>
            <T weight="medium" size={22}>{data.latest.styleRead}</T>
            {data.latest.chaos.length > 0 && (
              <View style={{ gap: 4 }}>
                <ChaosStrip chaos={data.latest.chaos} highlight={data.latest.highlight} />
                <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                  <T mono size={10} tone="muted">chaos you created, move by move</T>
                  <T mono size={10} tone="muted">{`${data.latest.chaos.length} moves`}</T>
                </View>
              </View>
            )}
            <View style={[s.row, { gap: 18 }]}>
              <Primary
                label={data.latest.moments.length === 1 ? "See the moment" : `See the ${data.latest.moments.length} moments`}
                onPress={() => router.push(`/games/${data.latest!.gameId}`)}
              />
              <Link label="Full review" onPress={() => router.push(`/games/${data.latest!.gameId}/review`)} />
            </View>
          </Card>

          <Card>
            <View style={[s.row, { alignItems: "baseline", flexWrap: "wrap", gap: 10 }]}>
              <Label>{`Brilliant · last ${data.brilliant.games}`}</Label>
              {quiet ? (
                <T mono size={20} tone="faint">hidden this week</T>
              ) : (
                <T mono size={32} tone={data.brilliant.pct == null ? "faint" : "accentText"}>
                  {data.brilliant.pct == null ? "—" : `${data.brilliant.pct.toFixed(1)}%`}
                </T>
              )}
              {!quiet && data.brilliant.pct != null && data.brilliant.spread != null && (
                <T mono size={12} tone="faint">{`±${data.brilliant.spread.toFixed(1)}`}</T>
              )}
            </View>
            <Gauge value={quiet ? null : data.brilliant.pct} lo={data.brilliant.goalLo} hi={data.brilliant.goalHi} spread={data.brilliant.spread} />
            {!quiet && data.brilliant.gapLine && <T size={13} tone="ink2">{data.brilliant.gapLine}</T>}
            {!quiet && data.stats && (
              <View style={[s.row, { marginTop: 4, borderTopWidth: 1, borderColor: color.hair, paddingTop: 10 }]}>
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
