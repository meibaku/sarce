/** You (handoff screen 5): Brilliant with its trend, the fingerprint, references, time controls. */
import { router } from "expo-router";
import { useState } from "react";
import { View } from "react-native";
import { ChaosMapCard } from "@/components/chaos-map";
import { TrapsSetCard } from "@/components/traps-set";
import { Card, Choice, Edge, Label, Link, Loading, Screen, T, Uncalibrated, s } from "@/components/ui";
import { getYou } from "@/lib/api";
import { color, ramp } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

/** Reference players on the axes, as on the web; a dot appears once their games are scored. */
const REFS = ["Tal", "Shirov", "Morphy"] as const;

export default function You() {
  const { data, failed, reload } = useLoad(getYou);
  const [tc, setTc] = useState(0);
  const [ref, setRef] = useState<(typeof REFS)[number]>("Tal");
  // The chaos map has its own request, so it shows even when the heavier You data is slow or fails.
  if (failed || !data)
    return (
      <Screen title="you">
        {failed ? <Edge kind="offline" action="Try again" onAction={reload} /> : <Loading />}
        <ChaosMapCard />
        <TrapsSetCard />
      </Screen>
    );
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
          <Label>Against your references</Label>
          <View style={{ flexDirection: "row", gap: 6 }}>
            {REFS.map((r) => (
              <View key={r} style={{ flex: 1 }}>
                <Choice label={r} selected={ref === r} onPress={() => setRef(r)} />
              </View>
            ))}
          </View>
          {data.axes.map((a) => {
            const tal = a.refs?.[ref];
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
                      <T mono size={7} style={{ lineHeight: 9 }}>{ref[0]}</T>
                    </View>
                  )}
                  {a.you != null && <View style={[dot, { left: `${a.you}%`, backgroundColor: color.accent }]} />}
                </View>
              </View>
            );
          })}
          <T mono size={11} tone="muted">
            {data.references?.[ref]
              ? `filled = you · ${ref[0]} = ${ref}, ${data.references[ref].games} games scored the same way · no ranking`
              : `filled = you · ${ref} is not scored in these terms yet · no ranking`}
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

      {/* The squeeze lens: once clearly winning (about +2), did your moves keep it tight? */}
      {data.grip && (
        <Card>
          <Label>Closing it out · the squeeze</Label>
          <T weight="medium" size={15}>{`${Math.round(((data.grip.moves - data.grip.gaveAir) / data.grip.moves) * 100)}% of your moves while winning kept the grip.`}</T>
          <T size={13} tone="ink2">{`${data.grip.squeezed} squeezed (left one or two replies that hold) · ${data.grip.gaveAir} gave air back, of ${data.grip.moves}.`}</T>
          {data.grip.latestLeak && (
            <Link
              label={`Latest one that gave air: ${data.grip.latestLeak.label} →`}
              onPress={() => router.push(`/games/${data.grip?.latestLeak?.gameId}/review`)}
            />
          )}
        </Card>
      )}

      {/* The swindle lens: once clearly losing (about −2), did your moves set real problems, and did they work? */}
      {data.fight && (
        <Card>
          <Label>Fighting back · the swindle</Label>
          <T weight="medium" size={15}>{`${data.fight.comebacks} of ${data.fight.lostPositions} games where you were clearly losing ended in a win or a draw.`}</T>
          <T size={13} tone="ink2">{`While losing you set a real problem with ${Math.round((data.fight.set / data.fight.moves) * 100)}% of your moves; ${data.fight.sprung} were sprung.`}</T>
          {data.fight.latestSprung && (
            <Link label={`Latest one that worked: ${data.fight.latestSprung.label} →`} onPress={() => router.push(`/games/${data.fight?.latestSprung?.gameId}/review`)} />
          )}
        </Card>
      )}

      {/* The clock lens: time as style, scaled to each game's starting clock. */}
      {data.clock && (
        <Card>
          <Label>Where your time went</Label>
          <T weight="medium" size={15}>{`${data.clock.criticalAvgS ?? "–"} s on moves where one move was clearly best, ${data.clock.easyAvgS ?? "–"} s on the rest.`}</T>
          <T size={13} tone="ink2">{`${data.clock.rushed} of ${data.clock.critical} critical moves were rushed · ${data.clock.lingered} easy moves took a long think.`}</T>
          <T mono size={11} tone="muted">{`won on time ${data.clock.wonOnTime} · lost on time ${data.clock.lostOnTime}`}</T>
        </Card>
      )}

      {data.sacrifices && (
        <Card>
          <Label>Your sacrifices</Label>
          <T size={14}>{`${data.sacrifices.played} played · ${data.sacrifices.held} held · ${data.sacrifices.withNotes} with notes`}</T>
          <Link label="Open the library →" onPress={() => router.push("/library")} />
        </Card>
      )}

      <ChaosMapCard />
      <TrapsSetCard />
    </Screen>
  );
}

const dot = { position: "absolute", marginLeft: -7, width: 14, height: 14, borderRadius: 7, alignItems: "center", justifyContent: "center" } as const;
