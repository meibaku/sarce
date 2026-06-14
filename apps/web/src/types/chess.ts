export type MoveQuality =
  | "best"
  | "excellent"
  | "good"
  | "inaccuracy"
  | "mistake"
  | "blunder"
  | "miss"
  | "brilliant";

export type MoveSignal =
  | "forced"
  | "top_engine_choice"
  | "top_three_choice"
  | "clearly_best"
  | "sacrifice"
  | "exchange_sacrifice"
  | "brilliant_sacrifice"
  | "evaluation_swing"
  | "tactical_resource"
  | "momentum_shift"
  | "breakthrough_sacrifice"
  | "missed_tactic"
  | "critical_error"
  | "clean_move";

export type GamePhase = "opening" | "middlegame" | "endgame";

export interface PrincipalVariation {
  rank: number;
  uci: string | null;
  san: string | null;
  eval: number | null;
}

export interface MainlineMove {
  ply: number;
  uci: string;
  san: string;
  fen: string;
}

export interface MoveQualityDistribution {
  best: number;
  excellent: number;
  good: number;
  inaccuracy: number;
  mistake: number;
  blunder: number;
  miss: number;
  brilliant: number;
}

export interface GameSummary {
  id: string;
  playedAt: string;
  opponent: string;
  opponentRating: number | null;
  result: "win" | "loss" | "draw";
  timeControl: string | null;
  analysisStatus: "pending" | "processing" | "complete" | "failed";
  brilliantPct: number | null;
  totalMoves: number | null;
}

export interface AnalyzedMove {
  ply: number;
  uci: string;
  san: string | null;
  quality: MoveQuality;
  cpLoss: number | null;
  evalBefore: number | null;
  evalAfter: number | null;
  isBrilliant: boolean;
  phase: GamePhase | null;
  signals: MoveSignal[];
  highlight: string | null;
  bestUci: string | null;
  bestSan: string | null;
  pv: PrincipalVariation[];
}

export interface GameDetail extends GameSummary {
  userColor: "white" | "black" | null;
  distribution: MoveQualityDistribution | null;
  initialFen: string;
  mainline: MainlineMove[];
  moves: AnalyzedMove[];
}

export interface UserBaseline {
  brilliantPct: number;
  distribution: MoveQualityDistribution;
  gamesAnalyzed: number;
  targetBrilliantMin: number;
  targetBrilliantMax: number;
}

export interface StyleVectorV1 {
  version: 1;
  brilliantPct: number;
  sacrificeRate: number;
  tacticalComplexity: number;
  evalVolatility: number;
  distribution: MoveQualityDistribution;
  signalDistribution?: Record<string, number>;
}

export interface ReferenceBenchmark {
  playerName: string;
  brilliantPct: number;
  distribution: MoveQualityDistribution;
  gamesSampled: number;
  status?: string;
}

export interface TimelinePoint {
  date: string | null;
  brilliantPct: number;
  opponent: string | null;
}

export interface StyleOpening {
  eco: string | null;
  name: string;
  games: number;
}

export interface StyleProfile {
  gamesAnalyzed: number;
  styleLabel: string;
  favoriteOpening: { eco: string | null; name: string } | null;
  openings: StyleOpening[];
  phaseDistribution: Record<string, number>;
  signalDistribution: Record<string, number>;
  resultDistribution: Record<string, number>;
  timeControlDistribution: Record<string, number>;
  qualityDistribution: MoveQualityDistribution;
}

export interface StyleMoment {
  gameId: string;
  playedAt: string | null;
  opponent: string | null;
  result: "win" | "loss" | "draw" | null;
  ply: number;
  uci: string;
  san: string | null;
  quality: MoveQuality;
  cpLoss: number | null;
  evalBefore: number | null;
  evalAfter: number | null;
  isBrilliant: boolean;
  phase: GamePhase | null;
  signals: MoveSignal[];
  highlight: string | null;
  bestUci: string | null;
  bestSan: string | null;
  pv: PrincipalVariation[];
}

export const EMPTY_DISTRIBUTION: MoveQualityDistribution = {
  best: 0,
  excellent: 0,
  good: 0,
  inaccuracy: 0,
  mistake: 0,
  blunder: 0,
  miss: 0,
  brilliant: 0,
};

export const TAL_BENCHMARK: ReferenceBenchmark = {
  playerName: "Mikhail Tal",
  brilliantPct: 0,
  distribution: EMPTY_DISTRIBUTION,
  gamesSampled: 0,
  status: "pending",
};
