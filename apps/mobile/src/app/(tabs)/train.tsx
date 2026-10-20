/**
 * Train (handoff screen 8): one queue; play the move on the board and the server checks it, or ask
 * for the answer; then "How sure were you?" schedules it (tomorrow / 3 days / 9 days).
 */
import { useState } from "react";
import { View } from "react-native";
import type { Confidence, DrillCheck } from "@sarce/types";
import { Board, nextSelection } from "@/components/board";
import { Card, Choice, Edge, Link, Loading, Screen, T, s } from "@/components/ui";
import { answerDrill, checkDrill, getTrain } from "@/lib/api";
import { useLoad } from "@/lib/use-load";

const CONFIDENCE: [Confidence, string, string][] = [
  ["guessed", "Guessed", "Back tomorrow. Guesses come round quickly."],
  ["unsure", "Unsure", "Back in 3 days."],
  ["sure", "Sure", "Back in 9 days. That one is sticking."],
];

export default function Train() {
  const { data, failed, reload } = useLoad(getTrain);
  const [index, setIndex] = useState(0);
  const [sel, setSel] = useState<string | null>(null);
  const [check, setCheck] = useState<DrillCheck | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [answered, setAnswered] = useState<Confidence | null>(null);

  if (failed || !data) return <Screen title="train">{failed ? <Edge kind="offline" action="Try again" onAction={reload} /> : <Loading />}</Screen>;
  if (data.items.length === 0) {
    return <Screen title="train"><Edge kind="too-few" detail="Drills come back when they're due. Play a game and new ones arrive from it." /></Screen>;
  }
  const d = data.items[Math.min(index, data.items.length - 1)];
  const legal = d.legal ?? [];
  const held = check ? check.matched || check.sound === true : false;

  function open(i: number) {
    setIndex(i);
    setSel(null);
    setCheck(null);
    setRevealed(false);
    setAnswered(null);
  }

  function onSquare(sq: string) {
    if (check) return;
    const next = nextSelection(legal, sel, sq);
    setSel(next.selected);
    if (next.move) checkDrill(d.fen, next.move, d.answer, d.source).then(setCheck).catch(() => null);
  }

  return (
    <Screen title="train">
      <View style={s.row}>
        <T weight="medium" size={22}>One queue</T>
        <T mono size={11} tone="muted" style={{ flex: 1 }} numberOfLines={1}>
          {data.focus ? `aimed at ${data.focus.toLowerCase()}` : `${data.waiting} waiting`}
        </T>
      </View>
      <View style={{ gap: 6 }}>
        {data.items.map((item, i) => (
          <Choice key={item.key} label={`${i + 1}  ${item.title}`} selected={i === index} onPress={() => open(i)} />
        ))}
      </View>
      <Card lead>
        <T mono size={11} tone="muted">{`${d.source} · ${d.meta}`}</T>
        <T weight="medium" size={17}>{d.title}</T>
        <T size={13} tone="ink2">{d.detail}</T>
        <Board
          fen={check?.fen ?? d.fen}
          orientation={d.fen.split(" ")[1] === "b" ? "black" : "white"}
          selected={sel}
          targets={sel ? legal.filter((m) => m.startsWith(sel)).map((m) => m.slice(2, 4)) : []}
          onSquare={check ? undefined : onSquare}
        />
        {check ? (
          <View style={{ gap: 4 }}>
            <T mono weight="medium" size={13} tone={held ? "sound" : "muted"}>
              {`${check.san} · ${check.matched ? "found" : check.sound === true ? "holds" : check.sound === false ? "didn't hold" : "played"}`}
            </T>
            <T size={13} tone="ink2">{check.line}</T>
            <Link label="Try again" onPress={() => setCheck(null)} />
          </View>
        ) : (
          <>
            <T size={12} tone="muted">Your move: tap a piece, then a highlighted square.</T>
            {d.answer && (revealed ? <T mono size={13} tone="accentText">{`Answer: ${d.answer}`}</T> : <Link label="Show the answer" onPress={() => setRevealed(true)} />)}
          </>
        )}
        <T weight="medium" size={14}>How sure were you?</T>
        <View style={{ flexDirection: "row", gap: 6 }}>
          {CONFIDENCE.map(([v, label]) => (
            <View key={v} style={{ flex: 1 }}>
              <Choice
                label={label}
                selected={answered === v}
                onPress={() => {
                  setAnswered(v);
                  answerDrill(d.key, v).catch(() => null);
                }}
              />
            </View>
          ))}
        </View>
        {answered && <T size={13} tone="ink2">{CONFIDENCE.find(([v]) => v === answered)?.[2]}</T>}
      </Card>
    </Screen>
  );
}
