/**
 * "Why this move?" on the phone (the web's components/review/why-panel.tsx): the badge's reason, each
 * Brilliant rule as a check with its number, the problem's numbers, and lines to step through.
 */
import { useState } from "react";
import { Pressable, View } from "react-native";
import { Board } from "@/components/board";
import { Card, Label, Link, Loading, T, s } from "@/components/ui";
import { getWhy, reportBrilliant } from "@/lib/api";
import { color } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

export function WhyCard({ gameId, ply, orientation, onClose }: { gameId: string; ply: number; orientation: "white" | "black"; onClose: () => void }) {
  const { data, failed } = useLoad(() => getWhy(gameId, ply), `${gameId}:${ply}`);
  const [line, setLine] = useState(0);
  const [step, setStep] = useState(1);
  const [reportLine, setReportLine] = useState<string | null>(null);
  if (failed) return <Card><T size={13} tone="muted">This move hasn&apos;t been analysed yet.</T><Link label="Close" onPress={onClose} /></Card>;
  if (!data) return <Loading />;
  const current = data.lines[line];
  const fen = step === 0 || !current ? data.fenBefore : current.steps[Math.min(step, current.steps.length) - 1].fen;
  return (
    <Card lead>
      <View style={s.row}>
        <Label accent>{`Why ${data.label}?`}</Label>
        <View style={{ flex: 1 }} />
        <Link label="Close" tone="muted" onPress={onClose} />
      </View>
      <T weight="medium" size={15}>{data.badge}</T>
      <T weight="medium" size={13}>{`${data.isBrilliant ? "Why it is Brilliant" : "Why it isn't Brilliant"} · ${data.brilliant.filter((c) => c.passed).length} of ${data.brilliant.length}`}</T>
      {data.brilliant.map((c) => (
        <View key={c.rule} style={{ flexDirection: "row", gap: 8 }}>
          <T mono weight="medium" tone={c.passed ? "sound" : "faint"}>{c.passed ? "✓" : "·"}</T>
          <T size={13} tone="ink2" style={{ flex: 1 }}>{`${c.rule}. ${c.detail}`}</T>
        </View>
      ))}
      {!data.isBrilliant &&
        (reportLine || data.reported ? (
          <T size={12} tone="muted">{reportLine ?? "You said Chess.com called this Brilliant."}</T>
        ) : (
          <Link
            label="Chess.com called this Brilliant"
            tone="muted"
            onPress={() => reportBrilliant(gameId, ply).then((r) => setReportLine(r.line)).catch(() => setReportLine("That didn't save. Try again."))}
          />
        ))}
      {data.chaos.pFail && (
        <T size={12} tone="muted">{`${data.chaos.faced ? "The problem you faced" : "The problem you set"}: ${data.chaos.pFail.map((p, i) => `${data.chaos.rungs[i]} ${Math.round(p * 100)}%`).join(" · ")} miss every safe reply${data.chaos.safeReplies.length ? ` (safe: ${data.chaos.safeReplies.join(", ")})` : ""}.`}</T>
      )}
      <Board fen={fen} orientation={orientation} maxSize={300} />
      <View style={[s.row, { justifyContent: "center" }]}>
        <Link label="‹ back" onPress={() => setStep((n) => Math.max(0, n - 1))} />
        <T mono size={11} tone="muted">{step === 0 ? "before your move" : `${step} / ${current?.steps.length ?? 0}`}</T>
        <Link label="next ›" onPress={() => setStep((n) => Math.min(current?.steps.length ?? 0, n + 1))} />
      </View>
      {data.lines.map((ln, i) => (
        <Pressable
          key={`${ln.title}-${i}`}
          onPress={() => {
            setLine(i);
            setStep(1);
          }}
          style={{ borderWidth: 1.5, borderRadius: 6, padding: 10, gap: 2, borderColor: ln.kind === "brilliant" ? color.accent : i === line ? color.ink : color.line2, backgroundColor: i === line ? color.accentTint : color.surface }}
        >
          <T weight="medium" size={13}>{`${ln.title}  ${ln.eval}`}</T>
          <T size={12} tone="ink2">{ln.note}</T>
          <T mono size={12}>{ln.steps.map((st) => st.san).join(" ")}</T>
        </Pressable>
      ))}
    </Card>
  );
}
