/**
 * Summary (handoff screen 3): the game in one line, Brilliant this game against your average, the
 * moments, then at most the question budget's questions (felt like you / check-in / intent).
 */
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { Share, View } from "react-native";
import type { CheckinAnswer, FeltAnswer, SummaryQuestion } from "@sarce/types";
import { Badge, Card, Choice, Edge, Gauge, Label, Link, Loading, Primary, Screen, T, Uncalibrated, s } from "@/components/ui";
import { Mascot } from "@/components/mascot";
import { WEB_BASE, answerCheckin, createShare, getSummary, setFelt } from "@/lib/api";
import { useLoad } from "@/lib/use-load";

const FELT: [FeltAnswer, string][] = [
  ["yes", "Yes"],
  ["partly", "Partly"],
  ["no", "Not really"],
];
const CHECKIN: [CheckinAnswer, string][] = [
  ["distracted", "Yes, I was distracted"],
  ["time_pressure", "Time pressure"],
  ["on_purpose", "No, I played it on purpose"],
  ["nothing", "Nothing special"],
];

function Question({ gameId, q }: { gameId: string; q: SummaryQuestion }) {
  const [felt, setFeltState] = useState<FeltAnswer | null>(q.kind === "felt" ? q.answer : null);
  const [checkin, setCheckin] = useState<CheckinAnswer | null>(q.kind === "checkin" ? q.answer : null);
  if (q.kind === "felt") {
    return (
      <Card lead>
        <Label accent>This game&apos;s one question</Label>
        <T weight="medium" size={18}>Did this game feel like you?</T>
        {FELT.map(([v, label]) => (
          <Choice key={v} label={label} selected={felt === v} onPress={() => { setFeltState(v); setFelt(gameId, v).catch(() => null); }} />
        ))}
      </Card>
    );
  }
  if (q.kind === "checkin") {
    return (
      <Card lead>
        <Label accent>This game&apos;s one question</Label>
        <T weight="medium" size={18}>{`Was something going on at ${q.label}?`}</T>
        <T size={12} tone="muted">{q.flagged ? "Your pace and choices changed around here. Only you know why." : "A random check-in: it tests whether Sarce's flags mean anything."}</T>
        {CHECKIN.map(([v, label]) => (
          <Choice key={v} label={label} selected={checkin === v} onPress={() => { setCheckin(v); answerCheckin(gameId, q.ply, v, q.flagged).catch(() => null); }} />
        ))}
      </Card>
    );
  }
  return (
    <Card lead>
      <Label accent>This game&apos;s one question</Label>
      <T weight="medium" size={18}>{`${q.label}: ${q.ask}`}</T>
      <Link label={q.answered ? "Noted · see it in Review" : "Answer in Review"} onPress={() => router.push(`/games/${gameId}/review`)} />
    </Card>
  );
}

export default function Summary() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data, failed, reload } = useLoad(() => getSummary(id), id);
  return (
    <Screen title={data ? `summary · ${data.opponent ?? "game"}` : "summary"} back>
      {failed ? (
        <Edge kind="offline" action="Try again" onAction={reload} />
      ) : !data ? (
        <Loading />
      ) : (
        <>
          {data.intention && (
            <Card>
              <View style={s.row}>
                <Label>Today&apos;s intention</Label>
                <T mono size={10} tone={data.intention.met ? "sound" : "muted"}>{data.intention.met === true ? "met" : data.intention.met === false ? "not this time" : "no chance to test"}</T>
              </View>
              <T size={13} tone="ink2">{`${data.intention.label}. ${data.intention.line}`}</T>
            </Card>
          )}
          <View style={s.row}>
            {/* The summary banner (handoff motion table): brilliant, else proud / relief / nod by result. */}
            <Mascot state={data.brilliant.count > 0 ? "brilliant" : data.result === "win" ? "proud" : data.result === "draw" ? "relief" : "nod"} size={48} />
            <T mono size={11} tone={data.outcome.accent ? "accentText" : "muted"}>{data.outcome.kicker}</T>
            {!data.calibrated && <Uncalibrated />}
          </View>
          <T weight="medium" size={22}>{data.headline}</T>
          <T size={13} tone="ink2">{data.outcome.text}</T>
          {data.analysing && <T mono size={11} tone="muted">Still scoring the rest of the moments…</T>}

          <Card>
            <Label>{`Brilliant this game · ${data.brilliant.count} of ${data.brilliant.of}`}</Label>
            <T mono weight="medium" size={26} tone="accentText">{`${data.brilliant.pct.toFixed(1)}%`}</T>
            <Gauge value={data.brilliant.pct} lo={data.brilliant.goalLo} hi={data.brilliant.goalHi} />
            {data.brilliant.rolling != null && <T size={12} tone="muted">{`Your average: ${data.brilliant.rolling.toFixed(1)}%`}</T>}
          </Card>

          <Card>
            <Label>The moments</Label>
            {data.moments.map((m) => (
              <View key={m.ply} style={s.row}>
                <Badge glyph={m.glyph} />
                <T size={13} tone="ink2" style={{ flex: 1 }}>{m.line}</T>
                {m.clock && <T mono size={11} tone="muted">{m.clock}</T>}
              </View>
            ))}
          </Card>

          {(data.questions ?? []).map((q) => (
            <Question key={q.kind} gameId={data.gameId} q={q} />
          ))}

          <Primary label="Review the moments" onPress={() => router.push(`/games/${data.gameId}/review`)} />
          {/* A read-only snapshot page: no opponent name, no notes; turn links off in the web app's Settings. */}
          <Link
            label="Share link"
            onPress={() =>
              createShare("summary", data.gameId)
                .then((l) => Share.share({ message: `${WEB_BASE}/s/${l.token}` }))
                .catch(() => null)
            }
          />
          <T mono size={11} tone="faint">{`style read ${data.styleRead}% you · ${data.styleReadVersion}`}</T>
        </>
      )}
    </Screen>
  );
}
