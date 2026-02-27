export interface ScoreCardSummary {
  symbol: string
  name: string
  grade: string
  score: number
  trend: string | null
  trend_emoji: string
  rsi: number | null
  signals: string[]
  swing_score?: number
  swing_grade?: string
  longterm_score?: number
  longterm_grade?: string
}

export interface ScoreCardSetup {
  entry: number
  target: number
  stop: number
  risk_reward: number
  signals: string[]
  target_level?: string
  stop_level?: string
}

export interface ScoreCardTechnicals {
  rsi: number | null
  rsi_label: string | null
  sma_20: number | null
  sma_50: number | null
  ema_12: number | null
  ema_26: number | null
  atr: number | null
  pivots: Record<string, number>
  support_resistance: { support: number[]; resistance: number[] }
  volume_ratio: number | null
  gap_pct: number | null
}

export interface ScoreCardHistoryEntry {
  date: string
  outcome: string
  entry: number | null
  r_multiple: number | null
  actual_return_pct: number | null
}

export interface ScoreCardHistory {
  appearances: number
  wins: number
  losses: number
  scratches: number
  win_rate: number | null
  avg_r: number | null
  recent: ScoreCardHistoryEntry[]
}

export interface TimeframeTarget {
  entry: number
  target: number
  stop: number
  risk_reward: number
  target_level: string
  stop_level: string
}

export interface TimeframeTargetExtended extends TimeframeTarget {
  support_zones: number[]
  resistance_zones: number[]
}

export interface MultiTfTargets {
  daily: TimeframeTargetExtended
  swing: TimeframeTargetExtended | null
  longterm: TimeframeTargetExtended | null
}

export interface TimeframeScore {
  score: number
  grade: string
  signals: string[]
  verdict: string
}

export interface MultiTfScores {
  daytrade: TimeframeScore
  swing: TimeframeScore | null
  longterm: TimeframeScore | null
}

export interface FundamentalMetrics {
  pe_ratio: number | null
  forward_pe: number | null
  pb_ratio: number | null
  ev_ebitda: number | null
  debt_equity: number | null
  current_ratio: number | null
  free_cash_flow: number | null
  revenue_growth: number | null
  eps_growth: number | null
  gross_margin: number | null
  operating_margin: number | null
  net_margin: number | null
  roe: number | null
  roa: number | null
}

export interface FundamentalScores {
  valuation: number | null
  profitability: number | null
  growth: number | null
  health: number | null
  composite: number
}

export interface Fundamentals {
  metrics: FundamentalMetrics
  scores: FundamentalScores
  highlights: {
    income: Record<string, number | null>
    balance: Record<string, number | null>
    cashflow: Record<string, number | null>
  }
  sector: string | null
  industry: string | null
  market_cap: number | null
}

export interface IndicatorAnalysis {
  key: string
  name: string
  weight_pct: number
  score: number
  score_label: string
  value_display: string
  what_it_measures: string
  current_reading: string
  why_it_matters: string
  score_explanation: string
  trading_insight: string
}

export interface ScoreCardFull extends ScoreCardSummary {
  verdict: string
  setup: ScoreCardSetup
  technicals: ScoreCardTechnicals
  history: ScoreCardHistory
  multi_tf_targets?: MultiTfTargets
  multi_tf_scores?: MultiTfScores
  fundamentals?: Fundamentals | null
  indicator_analyses?: IndicatorAnalysis[]
}
