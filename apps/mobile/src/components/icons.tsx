/**
 * Line icons and the rook mark for the phone app: the same paths as the web's components/ui/icons.tsx (24-unit
 * grid, 1.75 stroke, round joins), drawn with react-native-svg so they match the handoff instead of text glyphs.
 */
import Svg, { G, Path } from "react-native-svg";

export const ICONS = {
  home: "M4 11l8-7 8 7v9h-5v-6H9v6H4z",
  review: "M11 5a6 6 0 1 0 0 12a6 6 0 1 0 0-12M15.5 15.5L20 20",
  you: "M12 4a4 4 0 1 0 0 8a4 4 0 1 0 0-8M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6",
  train: "M4 12a8 8 0 0 1 14-5.3M18 3v4h-4M20 12a8 8 0 0 1-14 5.3M6 21v-4h4",
  play: "M8 5l11 7-11 7z",
  settings:
    "M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1",
} as const;

export type IconName = keyof typeof ICONS;

export function Icon({ name, size = 16, color }: { name: IconName; size?: number; color: string }) {
  return (
    <Svg viewBox="0 0 24 24" width={size} height={size}>
      <Path d={ICONS[name]} fill="none" stroke={color} strokeWidth={1.75} strokeLinejoin="round" strokeLinecap="round" />
    </Svg>
  );
}

/** The "open break" rook, unframed: the tight phone mark next to the wordmark. */
export function SarceMark({ height = 22, color }: { height?: number; color: string }) {
  return (
    <Svg viewBox="0 0 48 60" height={height} width={(height * 4) / 5}>
      <Path d="M13 32v9l-5 5q-2 2-2 4v6q0 2 2 2h32q2 0 2-2v-6q0-2-2-4l-5-5V24" fill="none" stroke={color} strokeWidth={3.4} strokeLinejoin="round" strokeLinecap="round" />
      <G transform="translate(5,-4) rotate(8 24 20)">
        <Path d="M8 34V23l-2-1q-3-1-3-4V6h7v5h5.5V6h7v5H33V6h7v12" fill="none" stroke={color} strokeWidth={3.4} strokeLinejoin="round" strokeLinecap="round" />
      </G>
    </Svg>
  );
}
