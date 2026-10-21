/**
 * A 3+0 game against a Sarce bot, as on the web (apps/web/src/components/play/bot-game.tsx): you
 * play White, the server is stateless, the bot's thinking time comes off its clock. A finished game
 * is saved with its clocks and analysed like any other; bot games stay out of your style metrics.
 */
import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { View } from "react-native";
import type { BotId, BotPosition } from "@sarce/types";
import { Board, nextSelection } from "@/components/board";
import { Card, Edge, Label, Link, Loading, Primary, Screen, T } from "@/components/ui";
import { botMove, saveBotGame, startBot } from "@/lib/api";
import { BOTS } from "@/lib/play";

const START_MS = 180_000;
type Result = { text: string; detail: string; outcome: "win" | "loss" | "draw" } | null;

const clock = (ms: number) => {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

export default function BotGame() {
  const { bot: raw } = useLocalSearchParams<{ bot?: string }>();
  const bot = (BOTS.some((b) => b.id === raw) ? raw : "defender") as BotId;
  const label = BOTS.find((b) => b.id === bot)?.label ?? "Sarce bot";
  const [pos, setPos] = useState<BotPosition | null>(null);
  const [failed, setFailed] = useState(false);
  const [sel, setSel] = useState<string | null>(null);
  const [sans, setSans] = useState<string[]>([]);
  const [mine, setMine] = useState(START_MS);
  const [theirs, setTheirs] = useState(START_MS);
  const [thinking, setThinking] = useState(false);
  const [started, setStarted] = useState(false);
  const [result, setResult] = useState<Result>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [moveCount, setMoveCount] = useState(0);
  // What gets saved: every move as UCI and the mover's clock after it.
  const ucis = useRef<string[]>([]);
  const clocks = useRef<number[]>([]);
  const last = useRef(0);
  const mineRef = useRef(START_MS);
  const theirsRef = useRef(START_MS);

  useEffect(() => {
    startBot().then(setPos).catch(() => setFailed(true));
  }, []);

  // One clock runs at a time, from your first move; running out ends the game from the tick itself.
  useEffect(() => {
    if (!pos || result || !started) return;
    last.current = Date.now();
    const id = setInterval(() => {
      const now = Date.now();
      const spent = now - last.current;
      last.current = now;
      const ref = thinking ? theirsRef : mineRef;
      ref.current -= spent;
      (thinking ? setTheirs : setMine)(ref.current);
      if (ref.current <= 0) {
        setResult(thinking ? { text: "You won on time", detail: `${label} ran out of clock.`, outcome: "win" } : { text: "Flagged", detail: "Your clock ran out.", outcome: "loss" });
      }
    }, 200);
    return () => clearInterval(id);
  }, [pos, thinking, result, started, label]);

  useEffect(() => {
    if (!result || saved || ucis.current.length === 0) return;
    saveBotGame({ bot, moves: ucis.current, result: result.outcome, clocks_ms: clocks.current }).then((r) => setSaved(r.gameId)).catch(() => null);
  }, [result, saved, bot]);

  const finish = useCallback(
    (p: BotPosition, you: boolean) => {
      if (p.status === "checkmate") setResult(you ? { text: "Checkmate. You won", detail: `Against ${label}.`, outcome: "win" } : { text: "Checkmated", detail: "Worth a look in your review.", outcome: "loss" });
      else if (p.status !== "ongoing") setResult({ text: "Draw", detail: p.status === "stalemate" ? "Stalemate." : "Drawn position.", outcome: "draw" });
    },
    [label],
  );

  async function onSquare(sq: string) {
    if (!pos || thinking || result || pos.turn !== "white") return;
    const next = nextSelection(pos.legal, sel, sq);
    setSel(next.selected);
    if (!next.move) return;
    setStarted(true);
    setThinking(true);
    try {
      const after = await botMove(pos.fen, next.move, bot, false);
      setSans((m) => [...m, after.playerSan ?? next.move!]);
      ucis.current.push(next.move);
      clocks.current.push(Math.max(0, Math.round(mineRef.current)));
      setMoveCount(ucis.current.length);
      setPos(after);
      if (after.status !== "ongoing") return finish(after, true);
      const reply = await botMove(after.fen, null, bot);
      if (reply.botSan) setSans((m) => [...m, reply.botSan as string]);
      if (reply.botUci) {
        ucis.current.push(reply.botUci);
        clocks.current.push(Math.max(0, Math.round(theirsRef.current)));
        setMoveCount(ucis.current.length);
      }
      setPos(reply);
      finish(reply, false);
    } catch {
      setFailed(true);
    } finally {
      setThinking(false);
    }
  }

  if (failed && !pos) return <Screen title="play" back><Edge kind="offline" /></Screen>;
  if (!pos) return <Screen title="play" back><Loading /></Screen>;
  return (
    <Screen title={`vs ${label}`} back>
      <T mono size={13} tone={thinking ? "accentText" : "muted"}>{`${label} ${clock(theirs)}${thinking ? " · thinking" : ""}`}</T>
      <Board fen={pos.fen} selected={sel} targets={sel ? pos.legal.filter((m) => m.startsWith(sel)).map((m) => m.slice(2, 4)) : []} onSquare={onSquare} />
      <T mono size={13} tone={!thinking && !result ? "accentText" : "muted"}>{`You ${clock(mine)}`}</T>
      {result ? (
        <Card lead>
          <T weight="medium" size={18}>{result.text}</T>
          <T size={13} tone="ink2">{result.detail}</T>
          {saved ? (
            <>
              <T mono size={11} tone="muted">Saved · analysing in the background</T>
              <Primary label="See the game" onPress={() => router.replace(`/games/${saved}`)} />
            </>
          ) : moveCount === 0 ? (
            <Primary label="Back to Play" onPress={() => router.back()} />
          ) : (
            <T mono size={11} tone="muted">Saving the game…</T>
          )}
        </Card>
      ) : (
        <Card>
          <Label>Moves</Label>
          <T mono size={13} tone="ink2">{sans.length === 0 ? "Your move." : sans.map((m, i) => (i % 2 === 0 ? `${i / 2 + 1}. ${m}` : m)).join(" ")}</T>
          <View style={{ alignSelf: "flex-start" }}>
            <Link label="Resign" tone="muted" onPress={() => setResult({ text: "Resigned", detail: "No harm done. Another one when you're ready.", outcome: "loss" })} />
          </View>
        </Card>
      )}
    </Screen>
  );
}
