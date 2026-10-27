import * as Linking from "expo-linking";
import * as Crypto from "expo-crypto";
import { useEffect, useState } from "react";
import { Pressable, TextInput, View } from "react-native";
import { Board } from "@/components/board";
import { Card, Choice, Label, Link, Loading, Primary, Screen, T } from "@/components/ui";
import {
  createLearningSession,
  enrolLearning,
  getLearningStatus,
  getNextLearningPresentation,
  submitLearningAttempt,
  withdrawLearning,
  type LearningPhase,
  type LearningPresentation,
  type LearningStatus,
} from "@/lib/api";
import { authConfigured, consumeAuthUrl, sendSignInLink } from "@/lib/auth";
import { color, font } from "@/lib/theme";

const PHASES: LearningPhase[] = ["baseline", "learning", "immediate", "day7", "day28"];
const LABEL: Record<LearningPhase, string> = {
  baseline: "Baseline", learning: "Learning", immediate: "Immediate check", day7: "Day 7", day28: "Day 28",
};
type Receipt = Awaited<ReturnType<typeof submitLearningAttempt>>;

export default function LearningEvidence() {
  const incoming = Linking.useLinkingURL();
  const [status, setStatus] = useState<LearningStatus | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const [email, setEmail] = useState("");
  const [invite, setInvite] = useState("");
  const [adult, setAdult] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [phase, setPhase] = useState<LearningPhase | null>(null);
  const [item, setItem] = useState<LearningPresentation | null>(null);
  const [square, setSquare] = useState<string | null>(null);
  const [noDanger, setNoDanger] = useState(false);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [clientAttemptId, setClientAttemptId] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function refresh() {
    try {
      setStatus(await getLearningStatus());
      setSignedIn(true);
      setMessage(null);
    } catch (error) {
      setSignedIn(!String(error).includes("401"));
      if (!String(error).includes("401")) setMessage("Learning Evidence is unavailable right now.");
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => void refresh(), 0);
    return () => clearTimeout(timer);
  }, []);
  useEffect(() => {
    if (!incoming) return;
    void consumeAuthUrl(incoming)
      .then((done) => { if (done) void refresh(); })
      .catch(() => setMessage("The sign-in link could not be completed."));
  }, [incoming]);

  async function emailLink() {
    if (!email.trim()) return;
    setBusy(true);
    try {
      await sendSignInLink(email.trim(), Linking.createURL("/learning"));
      setMessage("Check your email and open the sign-in link on this phone.");
    } catch (error) {
      setMessage(String(error));
    } finally { setBusy(false); }
  }

  async function enrol() {
    if (!invite.trim() || !adult) return;
    setBusy(true);
    try {
      await enrolLearning(invite.trim());
      setInvite("");
      await refresh();
    } catch {
      setMessage("That invitation cannot be used. Ask the study operator for a current link.");
    } finally { setBusy(false); }
  }

  async function loadNext(id: string) {
    const next = await getNextLearningPresentation(id);
    setItem(next.presentation);
    setSquare(null); setNoDanger(false); setConfidence(null); setReceipt(null); setStartedAt(Date.now());
    setClientAttemptId(next.presentation ? Crypto.randomUUID() : null);
    if (next.complete) {
      setSessionId(null);
      setMessage("This section is recorded. Return when the next study window opens.");
      await refresh();
    }
  }

  async function begin() {
    if (!status) return;
    setBusy(true); setMessage(null);
    try {
      const open = status.sessions.find((entry) => !entry.completedAt);
      const completed = new Set(status.sessions.filter((entry) => entry.completedAt).map((entry) => entry.phase));
      const nextPhase = open?.phase ?? PHASES.find((candidate) => !completed.has(candidate));
      if (!nextPhase) { setMessage("All scheduled sections are complete. Thank you for contributing evidence."); return; }
      const session = open ?? await createLearningSession(nextPhase);
      setSessionId(session.sessionId); setPhase(session.phase);
      await loadNext(session.sessionId);
    } catch (error) {
      setMessage(String(error).includes("outside its protocol window") ? "The next delayed check is not due yet." : "This section cannot start yet.");
    } finally { setBusy(false); }
  }

  async function answer() {
    if (!item || !clientAttemptId || confidence === null || (!square && !noDanger)) return;
    setBusy(true); setMessage(null);
    try {
      setReceipt(await submitLearningAttempt(item.presentationToken, {
        clientAttemptId,
        response: noDanger ? { noImmediateDanger: true } : { square: square! },
        confidence,
        latencyMs: Math.min(Date.now() - startedAt, 3_600_000),
      }));
    } catch { setMessage("Your answer was not acknowledged. It is safe to try saving it again."); }
    finally { setBusy(false); }
  }

  if (!authConfigured) return <Screen title="learning evidence" back><Card lead><T weight="medium" size={19}>Sign-in is not configured</T><T size={13} tone="ink2">Set the Expo Supabase URL and anon key before running this invite-only study.</T></Card></Screen>;
  if (!signedIn) return (
    <Screen title="learning evidence" back>
      <Card lead>
        <Label>Verified sign-in</Label>
        <T weight="medium" size={20}>Sign in before opening an invitation</T>
        <T size={13} tone="ink2">Sarce emails a one-time link. No password is handled here.</T>
        <TextInput
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          placeholder="you@example.com"
          style={inputStyle}
        />
        <Primary label={busy ? "Sending…" : "Email me a sign-in link"} onPress={emailLink} disabled={busy || !email.trim()} />
        {message && <T size={12} tone="muted">{message}</T>}
      </Card>
    </Screen>
  );
  if (!status) return <Screen title="learning evidence" back><Loading /></Screen>;
  if (!status.enrolled) return (
    <Screen title="learning evidence" back>
      <Card lead>
        <Label>Invite and consent</Label>
        <T weight="medium" size={20}>Join the piece-safety study</T>
        <T size={13} tone="ink2">Participation is voluntary. You can withdraw at any point, and this study never changes your style profile.</T>
        <TextInput value={invite} onChangeText={setInvite} autoCapitalize="none" placeholder="Invitation token" style={inputStyle} />
        <Pressable accessibilityRole="checkbox" accessibilityState={{ checked: adult }} onPress={() => setAdult(!adult)} style={{ flexDirection: "row", gap: 10 }}>
          <View style={{ width: 22, height: 22, borderWidth: 1.5, borderColor: adult ? color.accent : color.line2, backgroundColor: adult ? color.accentTint : color.surface, alignItems: "center", justifyContent: "center" }}>
            {adult && <T weight="semibold" size={13} tone="accentText">✓</T>}
          </View>
          <T size={13} tone="ink2" style={{ flex: 1 }}>I am 18 or older, understand this is a research pilot, and consent to its study records.</T>
        </Pressable>
        {message && <T size={12} tone="muted">{message}</T>}
        <Primary label="Accept invitation" onPress={enrol} disabled={busy || !adult || !invite.trim()} />
      </Card>
    </Screen>
  );
  if (status.enrollment?.withdrawnAt) return <Screen title="learning evidence" back><Card lead><T weight="medium" size={19}>Participation withdrawn</T><T size={13} tone="ink2">No new study sections will be offered.</T></Card></Screen>;
  if (!item) return (
    <Screen title="learning evidence" back>
      <Card lead>
        <Label>Learning Evidence</Label>
        <T weight="medium" size={20}>What can your opponent safely take right now?</T>
        <T size={13} tone="ink2">Unseen positions stay separate from style identity. Assessment schedules never adapt to confidence or previous answers.</T>
        <View style={{ flexDirection: "row", gap: 6, flexWrap: "wrap" }}>
          {PHASES.map((name) => <T key={name} mono size={10} tone="muted">{`${LABEL[name]} · ${status.sessions.some((entry) => entry.phase === name && entry.completedAt) ? "recorded" : "waiting"}`}</T>)}
        </View>
        {message && <T size={12} tone="muted">{message}</T>}
        <Primary label={busy ? "Opening…" : "Start or continue"} onPress={begin} disabled={busy} />
        <Link label="Withdraw from study" tone="muted" onPress={() => withdrawLearning().then(refresh).catch(() => null)} />
      </Card>
    </Screen>
  );

  const target = receipt?.feedback.target;
  const answerText = target?.noImmediateDanger ? "No immediate material danger" : `Square${(target?.squares?.length ?? 0) === 1 ? "" : "s"}: ${target?.squares?.join(", ") ?? "—"}`;
  return (
    <Screen title="learning evidence" back>
      <Card lead>
        <T mono size={11} tone="muted">{`${phase ? LABEL[phase] : "Study"} · item ${item.ordinal}`}</T>
        <Board fen={item.positionFen} orientation={item.positionFen.split(" ")[1] === "b" ? "black" : "white"} coords={false} selected={square} onSquare={receipt ? undefined : (next) => { setSquare(next); setNoDanger(false); }} />
      </Card>
      <Card>
        <Label>Unlabelled position</Label>
        <T weight="medium" size={20}>What can your opponent safely take right now?</T>
        {!receipt ? <>
          <Choice label="No immediate material danger" selected={noDanger} onPress={() => { setNoDanger(true); setSquare(null); }} />
          <T weight="medium" size={14}>How confident are you?</T>
          <View style={{ flexDirection: "row", gap: 6 }}>
            {[1, 2, 3, 4, 5].map((value) => <View key={value} style={{ flex: 1 }}><Choice label={String(value)} selected={confidence === value} onPress={() => setConfidence(value)} /></View>)}
          </View>
          {message && <T size={12} tone="muted">{message}</T>}
          <Primary label={busy ? "Recording…" : "Record answer"} onPress={answer} disabled={busy || confidence === null || (!square && !noDanger)} />
        </> : <>
          <T mono size={12} tone="accentText">Recorded durably</T>
          <T weight="medium" size={15}>{receipt.correct ? "You identified the relation." : "Look once more at the material relation."}</T>
          <T size={13} tone="ink2">{`Answer: ${answerText}`}</T>
          <Primary label={`Continue · ${receipt.remaining} left`} onPress={() => sessionId && loadNext(sessionId)} />
        </>}
      </Card>
    </Screen>
  );
}

const inputStyle = {
  height: 44,
  borderRadius: 6,
  borderWidth: 1.5,
  borderColor: color.line2,
  backgroundColor: color.surface,
  color: color.ink,
  paddingHorizontal: 12,
  fontFamily: font.sans,
  fontSize: 14,
};
