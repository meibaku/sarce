/**
 * Board (docs/DESIGN.md): 8×8 with a 1.5px ink border, radius 4. Pieces are circles at 64% of the
 * square: White as an outlined ink letter on white, Black as a white letter on ink. Squares that
 * mattered get an inset 2px accent ring plus a 6px corner tick, so they read without colour.
 */
const FILES = "abcdefgh";

/** Piece letters by square from a FEN's placement field. */
export function parseFen(fen: string): Record<string, string> {
  const pieces: Record<string, string> = {};
  const rows = fen.split(" ")[0].split("/");
  rows.forEach((row, r) => {
    let f = 0;
    for (const ch of row) {
      if (/\d/.test(ch)) f += Number(ch);
      else {
        pieces[`${FILES[f]}${8 - r}`] = ch;
        f += 1;
      }
    }
  });
  return pieces;
}

export function Board({
  fen,
  orientation = "white",
  hot = [],
  label,
  compact = false,
}: {
  fen: string;
  orientation?: "white" | "black";
  hot?: string[];
  label?: string;
  /** The Train drill board: max 300px, smaller pieces, no file letters. */
  compact?: boolean;
}) {
  const pieces = parseFen(fen);
  const squares: { sq: string; dark: boolean }[] = [];
  for (let r = 0; r < 8; r++) {
    for (let f = 0; f < 8; f++) {
      const file = orientation === "white" ? f : 7 - f;
      const rank = orientation === "white" ? 8 - r : r + 1;
      squares.push({ sq: `${FILES[file]}${rank}`, dark: (r + f) % 2 === 1 });
    }
  }
  const files = orientation === "white" ? FILES.split("") : FILES.split("").reverse();

  return (
    <div className={`flex flex-col gap-[10px] ${compact ? "w-full max-w-[300px]" : ""}`}>
      <div
        role="img"
        aria-label={label ?? "Chess board"}
        className="relative grid aspect-square w-full grid-cols-8 overflow-hidden rounded-[4px] border-[1.5px] border-ink"
      >
        {squares.map(({ sq, dark }) => {
          const piece = pieces[sq];
          const isHot = hot.includes(sq);
          const black = piece ? piece === piece.toLowerCase() : false;
          return (
            <div
              key={sq}
              className="relative grid place-items-center"
              style={{
                background: dark ? "var(--board-dark)" : "var(--surface)",
                boxShadow: isHot ? "inset 0 0 0 2px var(--accent)" : "none",
              }}
            >
              {isHot && (
                <span className="absolute top-[3px] right-[3px] h-[6px] w-[6px] border-t-2 border-r-2 border-accent" aria-hidden="true" />
              )}
              {piece && (
                <span
                  className={`grid place-items-center rounded-full border-[1.5px] border-ink font-mono font-medium ${
                    compact ? "h-[62%] w-[62%] text-[10px]" : "h-[64%] w-[64%] text-[12px]"
                  }`}
                  style={{ background: black ? "var(--ink)" : "var(--surface)", color: black ? "var(--surface)" : "var(--ink)" }}
                >
                  {piece.toUpperCase()}
                </span>
              )}
            </div>
          );
        })}
      </div>
      <div className={`flex justify-between px-1 font-mono text-[10px] text-muted ${compact ? "hidden" : ""}`} aria-hidden="true">
        {files.map((f) => (
          <span key={f}>{f}</span>
        ))}
      </div>
    </div>
  );
}
