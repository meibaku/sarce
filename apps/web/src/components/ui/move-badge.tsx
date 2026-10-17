/**
 * Move badges (docs/DESIGN.md): !! brilliant and !? speculative in accent, ✓ sound in green,
 * ?! check-in in amber, ? didn't hold in grey. Never red.
 */
export type MoveGlyph = "!!" | "!?" | "✓" | "?!" | "?";

const COLOR: Record<MoveGlyph, string> = {
  "!!": "var(--accent)",
  "!?": "var(--accent)",
  "✓": "var(--sound)",
  "?!": "var(--checkin)",
  "?": "var(--muted)",
};

const LABEL: Record<MoveGlyph, string> = {
  "!!": "Brilliant",
  "!?": "Speculative",
  "✓": "Sound",
  "?!": "Check-in",
  "?": "Didn't hold",
};

export function MoveBadge({ glyph, size = 26 }: { glyph: MoveGlyph; size?: number }) {
  const color = COLOR[glyph];
  return (
    <span
      role="img"
      aria-label={LABEL[glyph]}
      className="grid flex-none place-items-center rounded-full border-[1.5px] font-semibold"
      style={{ width: size, height: size, borderColor: color, color, fontSize: size >= 28 ? 12 : 11 }}
    >
      {glyph}
    </span>
  );
}
