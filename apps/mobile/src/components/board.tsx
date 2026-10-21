/**
 * The board, as on the web (apps/web/src/components/ui/board.tsx): circle-letter pieces, white
 * light squares and board-dark dark squares, an accent ring plus a corner tick on squares that
 * matter (ring and tick, so it never depends on colour alone), dots on legal targets.
 */
import { Pressable, View, useWindowDimensions } from "react-native";
import { T } from "@/components/ui";
import { color } from "@/lib/theme";

const FILES = "abcdefgh";

/** FEN placement → square ("e4") → piece letter (uppercase white, lowercase black). */
export function piecesOf(fen: string): Record<string, string> {
  const out: Record<string, string> = {};
  fen
    .split(" ")[0]
    .split("/")
    .forEach((row, r) => {
      let f = 0;
      for (const ch of row) {
        if (/\d/.test(ch)) f += Number(ch);
        else out[`${FILES[f++]}${8 - r}`] = ch;
      }
    });
  return out;
}

export function Board({
  fen,
  orientation = "white",
  hot = [],
  selected,
  targets = [],
  onSquare,
  maxSize = 360,
}: {
  fen: string;
  orientation?: "white" | "black";
  hot?: string[];
  selected?: string | null;
  targets?: string[];
  onSquare?: (square: string) => void;
  maxSize?: number;
}) {
  const { width } = useWindowDimensions();
  const size = Math.min(maxSize, width - 32);
  const cell = size / 8;
  const pieces = piecesOf(fen);
  const ranks = orientation === "white" ? [8, 7, 6, 5, 4, 3, 2, 1] : [1, 2, 3, 4, 5, 6, 7, 8];
  const files = orientation === "white" ? FILES.split("") : FILES.split("").reverse();

  return (
    <View
      accessibilityLabel="Chess board"
      style={{ width: size, height: size, borderWidth: 1.5, borderColor: color.ink, borderRadius: 4, overflow: "hidden", flexDirection: "row", flexWrap: "wrap", alignSelf: "center" }}
    >
      {ranks.flatMap((rank) =>
        files.map((file) => {
          const sq = `${file}${rank}`;
          const dark = (FILES.indexOf(file) + rank) % 2 === 1;
          const piece = pieces[sq];
          const isHot = hot.includes(sq) || selected === sq;
          const white = piece && piece === piece.toUpperCase();
          return (
            <Pressable
              key={sq}
              accessibilityLabel={sq}
              disabled={!onSquare}
              onPress={() => onSquare?.(sq)}
              style={{
                width: cell,
                height: cell,
                backgroundColor: dark ? color.boardDark : color.surface,
                alignItems: "center",
                justifyContent: "center",
                borderWidth: isHot ? 2 : 0,
                borderColor: color.accent,
              }}
            >
              {isHot && <View style={{ position: "absolute", top: 0, left: 0, width: 6, height: 6, backgroundColor: color.accent }} />}
              {piece ? (
                <View
                  style={{
                    width: cell * 0.62,
                    height: cell * 0.62,
                    borderRadius: cell,
                    borderWidth: 1.5,
                    borderColor: color.ink,
                    backgroundColor: white ? color.surface : color.ink,
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <T mono weight="medium" size={Math.max(9, cell * 0.26)} style={{ color: white ? color.ink : "#fff", lineHeight: undefined }}>
                    {piece.toUpperCase()}
                  </T>
                </View>
              ) : targets.includes(sq) ? (
                <View style={{ width: cell * 0.22, height: cell * 0.22, borderRadius: cell, backgroundColor: color.accent, opacity: 0.6 }} />
              ) : null}
            </Pressable>
          );
        }),
      )}
    </View>
  );
}

/** Click-to-move state for a board with server-supplied legal moves (UCI). */
export function nextSelection(legal: string[], selected: string | null, sq: string): { move?: string; selected: string | null } {
  if (selected) {
    const move = legal.find((m) => m.startsWith(selected + sq));
    if (move) return { move, selected: null };
  }
  return { selected: legal.some((m) => m.startsWith(sq)) ? sq : null };
}
