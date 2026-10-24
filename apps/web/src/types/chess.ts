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

export type ChaosVerdict = "real_chaos" | "calculated_risk" | "cheap_chaos";
export type SurvivalVerdict = "survived" | "missed";

/** Lens details are stored as JSON, so per-Elo maps are keyed by strings. */
export interface LensDetails {
  decided?: boolean;
  elo?: number | null;
  p_fail?: Record<string, number>;
  stake?: Record<string, number>;
  chaos?: Record<string, number>;
  safe_set?: string[];
  safe_set_complete?: boolean;
  objective_cost?: number | null;
  faced_chaos?: number;
}

export interface LensEntry {
  version: string;
  score: number | null;
  verdict: string | null;
  details: LensDetails;
}

export interface MoveLenses {
  ply: number;
  lenses: { soundness?: LensEntry; chaos?: LensEntry; survival?: LensEntry };
}

export interface GameLenses {
  gameId: string;
  moves: MoveLenses[];
  /** Remaining clock per ply (both players), or null when not stored. */
  clocksMs: (number | null)[] | null;
}

export interface ChaosGamePoint {
  gameId: string;
  playedAt: string | null;
  realChaos: number;
  cheapChaos: number;
}

export interface ChaosSummary {
  username: string;
  realChaos: number;
  cheapChaos: number;
  calculatedRisk: number;
  problemsFaced: number;
  survived: number;
  survivalRate: number | null;
  perGame: ChaosGamePoint[];
}

export interface Trap {
  fen: string;
  band: number;
  speed: string;
  frequency: number;
  commonReplyUci: string;
  commonReplyShare: number;
  epLoss: number;
  bestReplyUci: string | null;
  pFail: number | null;
  stake: number | null;
  eco: string | null;
}

export type MotifTag =
  | "sacrifice"
  | "fork"
  | "pin"
  | "skewer"
  | "discovered_attack"
  | "hanging_piece";
export type IdeaFamily = "gambit" | "king_attack" | "squeeze";
export type IdeaVerdict = "worked" | "refuted" | "fizzled";

export interface GameIdeas {
  gameId: string;
  tags: { ply: number; byUser: boolean; tag: MotifTag }[];
  ideas: {
    family: IdeaFamily;
    startPly: number;
    endPly: number;
    verdict: IdeaVerdict;
    isPivot: boolean;
  }[];
}

export interface ScoutingReport {
  id: string;
  username: string;
  source: "chess_com" | "lichess";
  gamesSampled: number;
  createdAt: string | null;
  report: {
    gamesSampled: number;
    results: Record<string, number>;
    timeControls: { name: string; games: number }[];
    openingsAsWhite: { name: string; games: number }[];
    openingsAsBlack: { name: string; games: number }[];
    motifsPer100Moves: Record<string, number>;
    ideasPerGame: Record<string, number>;
  };
}

/** GET /users/home (app/services/home.py). Numbers are null when they rest on fewer than 5 games. */
export interface HomeMoment {
  ply: number;
  san: string | null;
  glyph: "!!" | "!?" | "✓" | "?!" | "?";
  line: string;
}

export interface HomeApi {
  latest: {
    gameId: string;
    playedAt: string | null;
    opponent: string | null;
    result: "win" | "loss" | "draw" | null;
    userColor: "white" | "black" | null;
    timeControl: string | null;
    calibrated: boolean;
    styleRead: string;
    chaos: number[];
    highlight: number | null;
    moments: HomeMoment[];
  } | null;
  brilliant: {
    pct: number | null;
    spread: number | null;
    /** Wilson 95% interval, in percent (review F4). */
    lo?: number | null;
    hi?: number | null;
    games: number;
    goalLo: number;
    goalHi: number;
    gapLine?: string;
    /** Your next band: just above your likely range, on the way to the goal (plan 1.3). */
    nextLo?: number | null;
    nextHi?: number | null;
  };
  /** Games analysed since your last visit (plan 3.4a); null without `since` or when nothing is new. */
  session?: { games: number; feltLikeYou: number; realProblems: number; brilliant: number } | null;
  stats: {
    streak: number | null;
    real: number;
    cheap: number;
    soundRatio: number | null;
    trapsSurvived: number | null;
  } | null;
}

export type FeltAnswer = "yes" | "partly" | "no";

/** GET /games/{id}/summary (app/services/summary.py). */
/** Chaos budget (plan 3.9), in expected points: what setting problems cost, and what the replies gave back. */
export interface ChaosBudget {
  spent: number;
  back: number;
  net: number;
  problems: number;
  /** Replies outside the stored engine lines, left out of `back`. */
  unknown: number;
}

export interface SummaryApi {
  budget?: ChaosBudget | null;
  gameId: string;
  opponent: string | null;
  result: "win" | "loss" | "draw" | null;
  userColor: "white" | "black" | null;
  timeControl: string | null;
  calibrated: boolean;
  moves: number;
  headline: string;
  outcome: { kicker: string; accent: boolean; text: string };
  brilliant: { pct: number; count: number; of: number; rolling: number | null; goalLo: number; goalHi: number };
  moments: (HomeMoment & { clock: string | null })[];
  analysing: boolean;
  felt: FeltAnswer | null;
  styleRead: number;
  styleReadVersion: string;
  lichessUrl: string | null;
  /** This game's questions, already rotated and cut to the question budget. */
  questions?: SummaryQuestion[];
  /** How the game went against "Today I want to…", graded after the game. */
  intention?: { intent: string; label: string; met: boolean | null; line: string } | null;
}

export type CheckinAnswer = "distracted" | "time_pressure" | "on_purpose" | "nothing";

export type SummaryQuestion =
  | { kind: "felt"; answer: FeltAnswer | null }
  | { kind: "intent"; ply: number; label: string; ask: string; answered: boolean }
  | { kind: "checkin"; ply: number; label: string; flagged: boolean; answer: CheckinAnswer | null };

export type IntentType = "calculated" | "intuitive" | "bluff";

/** GET /games/{id}/review (app/services/review.py). */
export interface ReviewMoment extends HomeMoment {
  label: string;
  clock: string | null;
  kind: "set" | "survived" | "missed";
  ask: string;
  hot: string[];
  pFail: number[] | null;
  fallsLine: string;
  mirror: string;
  plan: string | null;
  intent: { type: IntentType | null; note: string } | null;
}

export interface ReviewApi {
  gameId: string;
  /** The game on its site, for "see this move there" (plan 3.4a): Chess.com `?move=N`, Lichess `#N`, N = ply + 1. */
  site?: { name: string; url: string; style: "query" | "hash" } | null;
  opponent: string | null;
  result: "win" | "loss" | "draw" | null;
  userColor: "white" | "black" | null;
  timeControl: string | null;
  calibrated: boolean;
  initialFen: string;
  positions: { ply: number; san: string; uci: string; fen: string }[];
  moments: ReviewMoment[];
  /** Squeeze lens: moves made while clearly winning that tightened the grip or gave air back. Edges in pawns. */
  /** Swindle lens: problems set while clearly losing; "sprung" when the opponent missed every safe reply. */
  /** Prophylaxis lens: real threats taken away with a quiet move, or let through. */
  theirIdeas?: { ply: number; label: string; verdict: "stopped" | "let_through"; threat: string | null; threatPawns: number }[];
  fightingBack?: { ply: number; label: string; verdict: "set" | "sprung"; edgeBefore: number; pFail: number | null }[];
  closingOut?: { ply: number; label: string; verdict: "squeezed" | "gave_air"; edgeBefore: number; edgeAfter: number; holding: number | null; best: string | null }[];
  ideas: { family: string; startPly: number; endPly: number; verdict: "worked" | "refuted" | "fizzled"; isPivot: boolean }[];
}

/** GET /users/you (app/services/you.py). Nulls rest on fewer than 5 games. */
export interface YouApi {
  games: number;
  goalLo: number;
  goalHi: number;
  brilliant: {
    pct: number | null;
    spread: number | null;
    /** Wilson 95% interval for Brilliant %, in percent (review F4). */
    lo?: number | null;
    hi?: number | null;
    weekly: (number | null)[];
    /** Brilliant % over rolling 20-game windows, oldest first, each with its interval. */
    rolling?: { pct: number; lo: number; hi: number; games: number; endAt: string | null }[];
    from: number | null;
    brilliantMoves: number;
    yourMoves: number;
    /** Week index (0–11) where the find-rate rule starts, for the "style v2" marker. */
    ruleChangedWeek?: number | null;
    findRateRule?: boolean;
  } | null;
  styleSchema?: number;
  /** `events`: observations behind each trait; below `minEvents` a trait is dashed (review F4). */
  fingerprint: { traits: string[]; levels: number[][]; sentence: string; events?: Record<string, number>; minEvents?: number } | null;
  /** `refs` holds each scored reference player's value on the axis (data/reference_axes.json). */
  axes: { name: string; you: number | null; refs?: Record<string, number | null> }[] | null;
  references?: Record<string, { games: number; model: string | null }>;
  /** `traits`: the nine traits in that class alone (plan 3.8), dashed under MIN_EVENTS, with a 95% range for shares. */
  timeControls: {
    class: "bullet" | "blitz" | "rapid";
    games: number;
    pct: number | null;
    spread: number | null;
    calibrated: boolean;
    traits?: Record<string, { value: number | null; lo: number | null; hi: number | null; events: number }>;
  }[];
  budget?: ChaosBudget | null;
  /** Where your two most-played classes differ beyond noise; `traits` empty when they overlap. */
  timeGap?: { classes: string[]; traits: { trait: string; more: string; less: string; ratio: number }[]; sentence: string } | null;
  /** Converting advantages (squeeze lens) across the window; null before any clearly winning position. */
  /** Fighting back (swindle lens): problems set while clearly losing, and games saved from lost positions. */
  fight?: {
    moves: number;
    set: number;
    sprung: number;
    lostPositions: number;
    comebacks: number;
    latestSprung: { gameId: string; ply: number; label: string; opponent: string | null; result: string | null } | null;
  } | null;
  /** Stopping their ideas (prophylaxis lens). */
  foresight?: {
    threats: number;
    stopped: number;
    met: number;
    letThrough: number;
    latestStopped: { gameId: string; ply: number; label: string; threat: string | null; opponent: string | null } | null;
  } | null;
  /** Where your time went (clock lens). */
  clock?: { moves: number; criticalAvgS: number | null; easyAvgS: number | null; rushed: number; lingered: number; critical: number; wonOnTime: number; lostOnTime: number } | null;
  grip?: { moves: number; squeezed: number; gaveAir: number; latestLeak: { gameId: string; ply: number; label: string; opponent: string | null } | null } | null;
  survival: {
    gameId: string;
    ply: number;
    opponent: string | null;
    moveNumber: number;
    survived: boolean;
    reply: string | null;
    pFail: number | null;
    clock: string | null;
    timeControl: string | null;
    trapsSurvived: number | null;
  } | null;
  sacrifices: { played: number; held: number; withNotes: number } | null;
}

/** GET /users/sacrifices (app/services/library.py). */
export interface SacrificeRow {
  gameId: string;
  ply: number;
  label: string;
  glyph: "!!" | "!?" | "✓" | "?!" | "?";
  type: string;
  material: number;
  opponent: string | null;
  playedAt: string | null;
  held: boolean;
  note: string | null;
  /** The game's opening (games.eco / games.opening); null for games imported before ECO extraction. */
  eco?: string | null;
  opening?: string | null;
}

/** GET /users/recap (app/services/recap.py). */
export interface RecapApi {
  week: string;
  games: number;
  feltLikeYou: number;
  bars: { gameId: string; styleRead: number; you: boolean }[];
  /** `trend` is "up"/"down" only when this week's and last week's intervals separate (review F4). */
  brilliant: { pct: number | null; spread: number | null; lo?: number | null; hi?: number | null; games: number; change: number | null; trend?: "up" | "down" | null };
  best: { gameId: string; ply: number; label: string } | null;
  lastFocus: { id: string; label: string | null; line: string | null } | null;
  streakWeeks: number;
  focuses: { id: string; label: string }[];
}

export type FocusKind = "weekly" | "today";

/** GET /users/train (app/services/train.py). */
export interface DrillItem {
  key: string;
  source: string;
  meta: string;
  title: string;
  detail: string;
  fen: string;
  answer: string | null;
  gameId: string | null;
  ply: number | null;
  /** Legal moves in `fen`, as UCI, so the board can offer targets. */
  legal?: string[];
}

/** Your move in a drill, checked on the server. `sound` is null when the engine couldn't say. */
export interface DrillCheck {
  san: string;
  uci: string;
  matched: boolean;
  sound: boolean | null;
  line: string;
  fen: string;
}

export interface TrainApi {
  band: number;
  items: DrillItem[];
  waiting: number;
  focus: string | null;
}

export type Confidence = "guessed" | "unsure" | "sure";

/** Sarce bots (app/services/bots.py): stateless positions with their legal moves. */
export type BotId = "defender" | "tal" | "swindler";

export interface BotPosition {
  fen: string;
  legal: string[];
  status: "ongoing" | "checkmate" | "stalemate" | "draw";
  turn: "white" | "black";
  playerSan?: string | null;
  botUci?: string | null;
  botSan?: string | null;
}

/** GET/PUT /users/settings (app/services/settings_store.py). */
export interface SettingsApi {
  goalLo: number;
  goalHi: number;
  questionBudget: 0 | 1 | 2;
  quietUntil: string | null;
  sources: "chess_com" | "lichess" | "both";
  theme: "light" | "dark" | "system";
  playfulMascot: boolean;
  motion: "system" | "full" | "reduced";
  chessComUsername?: string | null;
  lichessUsername?: string | null;
  /** Opt-in: screenshot reading and video summaries are sent to Anthropic (apps/api/app/services/ai.py). */
  aiHelp?: boolean;
  /** Whether the server has Claude credentials at all (read-only). */
  aiAvailable?: boolean;
  kept?: { games: number; notes: number };
}

/** A saved position (GET /users/positions); `source_*`, `excerpt` and `ai_summary` when it came from a video. */
export interface SavedPosition {
  id: string;
  fen: string;
  title: string;
  note: string;
  best_san: string | null;
  game_id: string | null;
  ply: number | null;
  source_url: string | null;
  source_time_s: number | null;
  excerpt: string;
  ai_summary: string;
  created_at: string;
}

/** GET /users/sync (app/services/sync.py). */
export interface SyncStatus {
  chessComUsername: string | null;
  lichessUsername: string | null;
  sources: "chess_com" | "lichess" | "both";
  lastSyncedAt: string | null;
  lastSyncErrors: string[];
  pending: number;
  processing: number;
  autoSync: boolean;
  chaosPass: boolean;
}
