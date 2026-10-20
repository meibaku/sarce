/**
 * Review (handoff screen 4). Moment chips, the board at the moment, and the question. The engine's
 * view stays hidden until you note your intent (Calculated / Intuitive / Bluff + text) or tap
 * "Show the engine": the plan is measured against itself first.
 */
import { useState } from "react";
import { Pressable, TextInput, View } from "react-native";
import type { IntentType, ReviewApi } from "@sarce/types";
import { Board } from "@/components/board";
import { Badge, Card, Choice, Edge, Label, Link, Loading, Primary, Screen, T, Uncalibrated, s } from "@/components/ui";
import { getReview, saveIntent, savePosition } from "@/lib/api";
import { color, font } from "@/lib/theme";
import { useLoad } from "@/lib/use-load";

const INTENTS: [IntentType, string][] = [
  ["calculated", "Calculated"],
  ["intuitive", "Intuitive"],
  ["bluff", "Bluff"],
];

function FallsChart({ pFail }: { pFail: number[] }) {
  const rungs = [800, 1200, 1600, 2000, 2400];
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 8, height: 64 }} accessibilityLabel="Who falls for this, by rating">
      {pFail.slice(0, 5).map((p, i) => (
        <View key={i} style={{ flex: 1, alignItems: "center", gap: 4 }}>
          <View style={{ width: "70%", height: Math.max(2, p * 44), backgroundColor: color.accent, borderRadius: 2 }} />
          <T mono size={10} tone="muted">{rungs[i]}</T>
        </View>
      ))}
    </View>
  );
}

export function ReviewBody({ gameId, back }: { gameId: string; back?: boolean }) {
  const { data, failed, reload, setData } = useLoad(() => getReview(gameId), gameId);
  const [index, setIndex] = useState(0);
  const [type, setType] = useState<IntentType | null>(null);
  const [text, setText] = useState("");
  const [shown, setShown] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const title = data ? `review · ${data.opponent ?? "game"}` : "review";
  if (failed || !data) {
    return <Screen title={title} back={back}>{failed ? <Edge kind="offline" action="Try again" onAction={reload} /> : <Loading />}</Screen>;
  }
  if (data.moments.length === 0) {
    return <Screen title={title} back={back}><Edge kind="analysing" /></Screen>;
  }

  const m = data.moments[Math.min(index, data.moments.length - 1)];
  const fen = data.positions[m.ply]?.fen ?? data.initialFen;
  const engineOpen = shown || !!m.intent;

  function go(i: number) {
    setIndex(i);
    setType(null);
    setText("");
    setShown(false);
  }

  async function save(d: ReviewApi) {
    const intent = { type, note: text };
    await saveIntent(gameId, m.ply, intent);
    setData({ ...d, moments: d.moments.map((x) => (x.ply === m.ply ? { ...x, intent } : x)) });
    setToast("Note saved.");
  }

  return (
    <Screen title={title} back={back}>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
        {data.moments.map((x, i) => (
          <Pressable
            key={x.ply}
            onPress={() => go(i)}
            accessibilityRole="button"
            accessibilityState={{ selected: i === index }}
            style={[s.row, { gap: 6, paddingHorizontal: 8, height: 32, borderRadius: 6, borderWidth: 1.5, borderColor: i === index ? color.accent : color.line2, backgroundColor: i === index ? color.accentTint : color.surface }]}
          >
            <Badge glyph={x.glyph} />
            <T mono size={12}>{x.label}</T>
          </Pressable>
        ))}
      </View>

      <Board fen={fen} orientation={data.userColor === "black" ? "black" : "white"} hot={m.hot} />

      <Card lead>
        <View style={s.row}>
          <Badge glyph={m.glyph} />
          <T weight="medium" size={15} style={{ flex: 1 }}>{`${m.label} · ${m.line}`}</T>
          {m.clock && <T mono size={11} tone="muted">{m.clock}</T>}
        </View>
        <T weight="medium" size={17}>{m.ask}</T>
        {m.intent ? (
          <View style={{ gap: 4 }}>
            <Label>You meant</Label>
            <T size={13} tone="ink2">{[m.intent.type, m.intent.note].filter(Boolean).join(" · ") || "No note"}</T>
          </View>
        ) : (
          <>
            <View style={{ flexDirection: "row", gap: 6 }}>
              {INTENTS.map(([v, label]) => (
                <View key={v} style={{ flex: 1 }}>
                  <Choice label={label} selected={type === v} onPress={() => setType(type === v ? null : v)} />
                </View>
              ))}
            </View>
            <TextInput
              value={text}
              onChangeText={setText}
              placeholder="What you saw, in your own words."
              placeholderTextColor={color.faint}
              multiline
              maxLength={2000}
              style={{ minHeight: 60, borderWidth: 1.5, borderColor: color.line2, borderRadius: 6, padding: 10, fontFamily: font.sans, fontSize: 13, color: color.ink }}
            />
            <View style={[s.row, { gap: 18 }]}>
              <Link label="Save note" onPress={() => save(data)} />
              {!shown && <Link label="Show the engine" onPress={() => setShown(true)} tone="muted" />}
            </View>
          </>
        )}
        {engineOpen && (
          <View style={{ gap: 6, borderTopWidth: 1, borderTopColor: color.hair, paddingTop: 10 }}>
            {m.plan && <T size={13} tone="ink2">{m.plan}</T>}
            <T size={13} tone="ink2">{m.mirror}</T>
          </View>
        )}
      </Card>

      {m.pFail && (
        <Card>
          <View style={s.row}>
            <Label>Who falls for this</Label>
            {!data.calibrated && <Uncalibrated />}
          </View>
          <FallsChart pFail={m.pFail} />
          <T size={13} tone="ink2">{m.fallsLine}</T>
        </Card>
      )}

      <View style={[s.row, { gap: 18 }]}>
        <Primary label="Next moment" onPress={() => go((index + 1) % data.moments.length)} />
        <Link
          label="Add to Train"
          onPress={() => {
            const before = m.ply > 0 ? data.positions[m.ply - 1]?.fen : data.initialFen;
            if (!before) return;
            savePosition({ fen: before, title: `vs ${data.opponent ?? "opponent"}, ${m.label}`, gameId, ply: m.ply })
              .then(() => setToast("Added to Train."))
              .catch(() => setToast("Couldn't add it. Try again."));
          }}
        />
      </View>
      {toast && <T mono size={11} tone="muted">{toast}</T>}
    </Screen>
  );
}
