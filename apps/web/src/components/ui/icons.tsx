/** Line icons on a 24-unit grid, 1.75 stroke, round joins (docs/DESIGN.md). */
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

export function Icon({ name, size = 16, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} className={className} style={{ overflow: "visible" }} aria-hidden="true">
      <path
        d={ICONS[name]}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.75}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

/**
 * The 7a "open break" rook: two open paths, the top lifted and turned. `framed` draws it in the
 * padded box the animated mark uses (desktop header, Home card); unframed is the tight phone mark.
 */
export function SarceMark({
  height = 20,
  framed = false,
  className,
}: {
  height?: number;
  framed?: boolean;
  className?: string;
}) {
  return (
    <svg
      viewBox={framed ? "-14 -18 76 84" : "0 0 48 60"}
      height={height}
      width={framed ? (height * 76) / 84 : (height * 4) / 5}
      className={className}
      style={{ overflow: "visible", display: framed ? "block" : undefined }}
      aria-hidden="true"
    >
      <path
        d="M13 32v9l-5 5q-2 2-2 4v6q0 2 2 2h32q2 0 2-2v-6q0-2-2-4l-5-5V24"
        fill="none"
        stroke="currentColor"
        strokeWidth={3.4}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <path
        d="M8 34V23l-2-1q-3-1-3-4V6h7v5h5.5V6h7v5H33V6h7v12"
        fill="none"
        stroke="currentColor"
        strokeWidth={3.4}
        strokeLinejoin="round"
        strokeLinecap="round"
        transform="translate(5,-4) rotate(8 24 20)"
      />
    </svg>
  );
}
