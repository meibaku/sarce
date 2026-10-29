/**
 * Board (docs/DESIGN.md): 8×8 with a 1.5px ink border, radius 4. Pieces are circles at 64% of the
 * square: White as an outlined ink letter on white, Black as a white letter on ink. Squares that
 * mattered get an inset 2px accent ring plus a 6px corner tick, so they read without colour.
 */
const FILES = "abcdefgh";
const GLYPHS: Record<string, string> = {
  K: "♔", Q: "♕", R: "♖", B: "♗", N: "♘", P: "♙",
  k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟",
};

function squarePoint(square: string, orientation: "white" | "black") {
  const file = FILES.indexOf(square[0]);
  const rank = Number(square[1]);
  const column = orientation === "white" ? file : 7 - file;
  const row = orientation === "white" ? 8 - rank : rank - 1;
  return { x: (column + 0.5) * 12.5, y: (row + 0.5) * 12.5 };
}

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
  onSquareClick,
  selected,
  targets = [],
  pieceStyle = "letters",
  arrow,
  coordinates = "outside",
}: {
  fen: string;
  orientation?: "white" | "black";
  hot?: string[];
  label?: string;
  /** The Train drill board: max 300px, smaller pieces, no file letters. */
  compact?: boolean;
  /** Makes squares clickable, for playing against a Sarce bot. */
  onSquareClick?: (square: string) => void;
  selected?: string | null;
  /** Legal destinations of the selected piece, shown as dots. */
  targets?: string[];
  /** Pilot-only richer pieces; the default preserves the normal product board. */
  pieceStyle?: "letters" | "glyphs";
  /** A stored played move, never an inferred recommendation. */
  arrow?: { from: string; to: string } | null;
  coordinates?: "outside" | "inside";
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
  const arrowFrom = arrow ? squarePoint(arrow.from, orientation) : null;
  const arrowTo = arrow ? squarePoint(arrow.to, orientation) : null;

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
          const Square = onSquareClick ? "button" : "div";
          return (
            <Square
              key={sq}
              {...(onSquareClick ? { type: "button" as const, onClick: () => onSquareClick(sq), "aria-label": sq } : {})}
              className="relative grid place-items-center border-0 p-0"
              style={{
                background: selected === sq ? "var(--accent-tint)" : dark ? "var(--board-dark)" : "var(--surface)",
                boxShadow: isHot || selected === sq ? "inset 0 0 0 2px var(--accent)" : "none",
              }}
            >
              {targets.includes(sq) && (
                <span className="absolute h-[22%] w-[22%] rounded-full bg-accent opacity-60" aria-hidden="true" />
              )}
              {isHot && (
                <span className="absolute top-[3px] right-[3px] h-[6px] w-[6px] border-t-2 border-r-2 border-accent" aria-hidden="true" />
              )}
              {piece && (
                <span
                  className={`relative z-10 grid place-items-center rounded-full border-[1.5px] border-ink font-mono font-medium ${
                    pieceStyle === "glyphs" ? "h-[76%] w-[76%] text-[clamp(22px,5vw,38px)] leading-none" : compact ? "h-[62%] w-[62%] text-[10px]" : "h-[64%] w-[64%] text-[12px]"
                  }`}
                  style={{ background: black ? "var(--ink)" : "var(--surface)", color: black ? "var(--surface)" : "var(--ink)" }}
                >
                  {pieceStyle === "glyphs" ? GLYPHS[piece] : piece.toUpperCase()}
                  {pieceStyle === "glyphs" && <span className="absolute right-[-2px] bottom-[-2px] grid h-4 w-4 place-items-center rounded-full border border-ink bg-surface text-[8px] text-ink" aria-hidden="true">{piece.toUpperCase()}</span>}
                </span>
              )}
              {coordinates === "inside" && sq[0] === files[0] && <span className="absolute left-1 top-0.5 font-mono text-[8px] text-muted" aria-hidden="true">{sq[1]}</span>}
              {coordinates === "inside" && sq[1] === (orientation === "white" ? "1" : "8") && <span className="absolute bottom-0.5 right-1 font-mono text-[8px] text-muted" aria-hidden="true">{sq[0]}</span>}
            </Square>
          );
        })}
        {arrowFrom && arrowTo && (
          <svg viewBox="0 0 100 100" className="pointer-events-none absolute inset-0 z-20 h-full w-full" aria-hidden="true">
            <defs><marker id="pilot-board-arrowhead" markerWidth="5" markerHeight="5" refX="3.5" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 Z" fill="var(--accent)" /></marker></defs>
            <line x1={arrowFrom.x} y1={arrowFrom.y} x2={arrowTo.x} y2={arrowTo.y} stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" markerEnd="url(#pilot-board-arrowhead)" opacity="0.9" />
          </svg>
        )}
      </div>
      <div className={`flex justify-between px-1 font-mono text-[10px] text-muted ${compact || coordinates === "inside" ? "hidden" : ""}`} aria-hidden="true">
        {files.map((f) => (
          <span key={f}>{f}</span>
        ))}
      </div>
    </div>
  );
}
