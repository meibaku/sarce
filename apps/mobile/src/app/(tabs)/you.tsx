/** You (handoff screen 5): Brilliant with its trend, the fingerprint, references, time controls. */
import { router } from "expo-router";
import { useState } from "react";
import { View } from "react-native";
import { Card, Choice, Edge, Label, Link, Loading, Screen, T, Uncalibrated, s } from "@/components/ui";
import { getYou } from "@/lib/api";
import { color, ramp } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

export default function You() {
  const { data, failed, reload } = useLoad(getYou);
  const [tc, setTc] = useState(0);
  if (failed || !data) return <Screen title="you">{failed ? <Edge kind="offline" action="Try again" onAction={reload} /> : <Loading />}</Screen>;
  if (data.games === 0) return <Screen title="you"><Edge kind="no-games" action="Connect an account" onAction={() => router.push("/onboarding")} /></Screen>;
  const weekly = data.brilliant?.weekly ?? [];
  const max = Math.max(15, ...weekly.map((w) => w ?? 0));
  const time = data.timeControls[tc];
  const fingerprint = data.fingerprint;
  return (
    <Screen title="you">
      <T weight="medium" size={22}>You, as a player</T>
      <Card lead>
        <Label>Brilliant</Label>
        <T mono weight="medium" size={34} tone={data.brilliant?.pct == null ? "faint" : "accentText"}>
          {data.brilliant?.pct == null ? "—" : `${data.brilliant.pct.toFixed(1)}%`}
        </T>
        {data.brilliant && <T size={12} tone="muted">{`${data.brilliant.brilliantMoves} brilliant of ${data.brilliant.yourMoves} of your moves · 12 weeks`}</T>}
        <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 3, height: 48 }} accessibilityLabel="Brilliant by week">
          {weekly.map((w, i) => (
            <View
              key={i}
              style={{
                flex: 1,
                height: w == null ? 2 : Math.max(2, (w / max) * 48),
                backgroundColor: w == null ? color.line : w >= data.goalLo && w <= data.goalHi ? color.accent : color.line3,
                borderRadius: 1,
              }}
            />
          ))}
        </View>
      </Card>

      {fingerprint && (
        <Card>
          <Label>Style fingerprint · 12 weeks</Label>
          {fingerprint.traits.map((trait, r) => (
            <View key={trait} style={s.row}>
              <T size={12} style={{ width: 72 }}>{trait}</T>
              <View style={{ flex: 1, flexDirection: "row", gap: 2 }}>
                {fingerprint.levels[r].map((lvl, i) => (
                  <View key={i} style={{ flex: 1, height: 14, borderRadius: 2, backgroundColor: ramp[Math.max(0, Math.min(7, lvl))] }} />
                ))}
              </View>
            </View>
          ))}
          <T size={12} tone="muted">{fingerprint.sentence}</T>
        </Card>
      )}

      {data.axes && (
        <Card>
          <Label>Against Tal</Label>
          {data.axes.map((a) => {
            const tal = a.refs?.Tal;
            return (
              <View key={a.name} style={{ gap: 4 }}>
                <View style={s.row}>
                  <T size={13} style={{ flex: 1 }}>{a.name}</T>
                  <T mono size={12} tone="accentText">{a.you == null ? "—" : String(a.you)}</T>
                </View>
                <View style={{ height: 16, justifyContent: "center" }}>
                  <View style={{ height: 1.5, backgroundColor: color.line2 }} />
                  {tal != null && (
                    <View style={[dot, { left: `${tal}%`, borderWidth: 1.5, borderColor: color.ink, backgroundColor: color.surface }]}>
                      <T mono size={7} style={{ lineHeight: 9 }}>T</T>
                    </View>
                  )}
                  {a.you != null && <View style={[dot, { left: `${a.you}%`, backgroundColor: color.accent }]} />}
                </View>
              </View>
            );
          })}
          <T mono size={11} tone="muted">
            {data.references?.Tal
              ? `filled = you · T = Tal, ${data.references.Tal.games} games scored the same way · no ranking`
              : "filled = you · Tal is not scored in these terms yet · no ranking"}
          </T>
        </Card>
      )}

      {data.timeControls.length > 0 && (
        <Card>
          <Label>By time control</Label>
          <View style={{ flexDirection: "row", gap: 6 }}>
            {data.timeControls.map((t, i) => (
              <View key={t.class} style={{ flex: 1 }}>
                <Choice label={t.class[0].toUpperCase() + t.class.slice(1)} selected={i === tc} onPress={() => setTc(i)} />
              </View>
            ))}
          </View>
          {time && (
            <View style={s.row}>
              <T mono weight="medium" size={20} tone={time.pct == null ? "faint" : "accentText"}>{time.pct == null ? "—" : `${time.pct.toFixed(1)}%`}</T>
              <T mono size={11} tone="muted">{`${time.games} games`}</T>
              {!time.calibrated && <Uncalibrated />}
            </View>
          )}
        </Card>
      )}

      {data.survival && (
        <Card>
          <Label>Survival · the defensive half</Label>
          <T weight="medium" size={15}>{`Hardest problem you faced lately: move ${data.survival.moveNumber} vs ${data.survival.opponent ?? "opponent"}`}</T>
          <Link label="Open it in Review" onPress={() => router.push(`/games/${data.survival?.gameId}/review`)} />
        </Card>
      )}

      {data.sacrifices && (
        <Card>
          <Label>Your sacrifices</Label>
          <T size={14}>{`${data.sacrifices.played} played · ${data.sacrifices.held} held · ${data.sacrifices.withNotes} with notes`}</T>
          <Link label="Open the library →" onPress={() => router.push("/library")} />
        </Card>
      )}
    </Screen>
  );
}

const dot = { position: "absolute", marginLeft: -7, width: 14, height: 14, borderRadius: 7, alignItems: "center", justifyContent: "center" } as const;
