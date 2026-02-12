export interface ScoreCardSummary {
  symbol: string
  name: string
  grade: string
  score: number
  trend: string | null
  trend_emoji: string
  rsi: number | null
  signals: string[]
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

export interface MultiTfTargets {
  daily: TimeframeTarget
  weekly: TimeframeTarget | null
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
  indicator_analyses?: IndicatorAnalysis[]
}
