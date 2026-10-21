/**
 * The rook mascot on native: the handoff's frame maths (lib/mascot-frames.ts) drawn with
 * react-native-svg, the same geometry as the web component (viewBox, neck break, eyes, badge, ring).
 * With the system's Reduce Motion on it holds the state's still pose (the handoff's REST frame).
 * Path drawing ("trace") needs pathLength, which native SVG lacks, so that one state shows drawn.
 */
import { useEffect, useState } from "react";
import { AccessibilityInfo } from "react-native";
import Svg, { Circle, ClipPath, Defs, Ellipse, G, Path, Polygon, Text as SvgText } from "react-native-svg";
import { C, D, REST as REST_POSES, S as STATES } from "@/lib/mascot-frames";
import { usePrefs } from "@/lib/prefs";

/** A frame: transforms, eyes, badge and ring for one instant (see lib/mascot-frames.ts). */
type Frame = { [key: string]: any };
const S = STATES as unknown as Record<string, (t: number, progress: number | null, loop: boolean) => Frame>;
const REST = REST_POSES as Record<string, number>;

export type MascotState =
  | "static" | "trace" | "tip" | "ring" | "brilliant" | "sound" | "checkin" | "uncalibrated" | "error" | "offline" | "empty" | "quiet"
  | "idle" | "nod" | "shake" | "look" | "think" | "bow" | "cheer" | "droop" | "sleep" | "hello" | "hop" | "curious" | "proud" | "shy" | "relief" | "stretch";

/** Rough length of the rook outline in viewBox units, for the dashed (offline / empty) states. */
const OUTLINE = 200;

function useReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduced).catch(() => undefined);
    const sub = AccessibilityInfo.addEventListener("reduceMotionChanged", setReduced);
    return () => sub.remove();
  }, []);
  return reduced;
}

export function Mascot({ state: wanted = "idle", size = 44, progress, eyes: wantEyes = true }: { state?: MascotState; size?: number; progress?: number; eyes?: boolean }) {
  const prefs = usePrefs();
  const systemReduced = useReducedMotion();
  // Playful off: the still mark, no eyes. Motion follows the setting, or the system when "system".
  const state = prefs.playful ? wanted : "static";
  const eyes = prefs.playful && wantEyes;
  const reduced = !prefs.playful || prefs.motion === "reduced" || (prefs.motion === "system" && systemReduced);
  const [t, setT] = useState(0);

  useEffect(() => {
    if (reduced) return;
    let raf = 0;
    const t0 = Date.now();
    const tick = () => {
      setT((Date.now() - t0) / 1000);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [reduced, state]);

  const fn = S[state] ?? S.static;
  const f: Frame = { draw: 1, dash: 0, lift: 0, tilt: null, dip: 0, op: 1, color: C.ink, ...fn(reduced ? (REST[state] ?? 0) : t, progress ?? null, !reduced) };
  const tilt = f.tilt == null ? 8 * f.lift : f.tilt;
  const sq = f.sq || 0;
  const [px, py] = f.pv ? [24, 25] : [24, 20];
  const showEyes = eyes && f.eyes;
  const es = f.es || 1;
  const blink = f.blink == null ? 1 : f.blink;
  const dashLo = f.dashed === "both" ? `${0.035 * OUTLINE} ${0.03 * OUTLINE}` : undefined;
  const dashHi = f.dashed ? `${0.035 * OUTLINE} ${0.03 * OUTLINE}` : undefined;
  const badge = f.badge as [string, string, number, boolean?] | undefined;
  const stroke = { fill: "none", strokeWidth: 3, strokeLinejoin: "round", strokeLinecap: "round", stroke: f.color } as const;

  return (
    <Svg width={(size * 76) / 84} height={size} viewBox="-14 -18 76 84" opacity={f.op} accessibilityLabel="Sarce">
      <Defs>
        <ClipPath id="lo">
          <Polygon points="-20,80 -20,36 0,34 48,22 68,17 68,80" />
        </ClipPath>
        <ClipPath id="hi">
          <Polygon points="-20,-30 68,-30 68,14 48,19 0,31 -20,36" />
        </ClipPath>
      </Defs>
      {f.ring != null && (
        <>
          <Circle cx={24} cy={30} r={37} fill="none" strokeWidth={2} stroke={C.line} />
          <Circle
            cx={24}
            cy={30}
            r={37}
            fill="none"
            strokeWidth={2}
            stroke={C.acc}
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 37}`}
            strokeDashoffset={2 * Math.PI * 37 * (1 - f.ring)}
            transform="rotate(-90 24 30)"
          />
        </>
      )}
      <G transform={`translate(${f.bx || 0} ${(f.by || 0) + 2 * f.dip}) rotate(${f.brot || 0} ${f.bpx || 24} 58) translate(24 58) scale(${1 + sq * 0.6} ${1 - sq}) translate(-24 -58)`}>
        <Path d={D} {...stroke} strokeDasharray={dashLo} clipPath="url(#lo)" />
        <G transform={`translate(${5 * f.lift + (f.hx || 0)} ${-4 * f.lift + (f.hy || 0)}) rotate(${tilt} ${px} ${py})`}>
          <Path d={D} {...stroke} strokeDasharray={dashHi} clipPath="url(#hi)" />
          {showEyes &&
            (
              [
                [19, f.wl],
                [29, f.wr],
              ] as [number, number | undefined][]
            ).map(([x, w]) => (
              <Ellipse key={x} cx={x + (f.ex || 0)} cy={16 + (f.ey || 0)} rx={1.6 * es} ry={Math.max(0.25, 1.6 * es * blink * (w == null ? 1 : w))} fill={f.color} />
            ))}
        </G>
      </G>
      {badge && badge[2] > 0 && (
        <G transform={`translate(50 -4) scale(${badge[2]})`}>
          <Circle cx={0} cy={0} r={9} fill="#fff" strokeWidth={1.6} stroke={badge[1]} strokeDasharray={badge[3] ? "2 1.6" : undefined} />
          <SvgText x={0} y={3.4} textAnchor="middle" fontSize={9.5} fontWeight="600" fill={badge[1]}>
            {badge[0]}
          </SvgText>
        </G>
      )}
    </Svg>
  );
}
