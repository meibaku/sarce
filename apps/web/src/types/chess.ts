export type MoveQuality =
  | "best"
  | "excellent"
  | "good"
  | "inaccuracy"
  | "mistake"
  | "blunder"
  | "miss"
  | "brilliant";

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
  brilliantPct: number;
  distribution: MoveQualityDistribution;
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
