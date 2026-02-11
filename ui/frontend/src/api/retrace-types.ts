export interface SnapshotMeta {
  date: string
  timestamp: string
  pick_count: number
  has_grading: boolean
  backfilled: boolean
  scoring_weights: Record<string, number>
  prompts_version: string
  digest_type?: string
}

export interface PickGrading {
  symbol: string
  score: number
  entry: number
  target: number
  stop: number
  signals: string[]
  trend: string
  outcome: 'win' | 'loss' | 'scratch' | 'ambiguous' | 'pending'
  next_day_date?: string
  next_day_open?: number
  next_day_high?: number
  next_day_low?: number
  next_day_close?: number
  hit_target?: boolean
  hit_stop?: boolean
  mfe?: number
  mae?: number
  actual_return?: number
  actual_return_pct?: number
  r_multiple?: number
  reason?: string
}

export interface GradingSummary {
  graded_at: string
  picks: PickGrading[]
  total_graded: number
  outcomes: Record<string, number>
  win_rate: number
  avg_r_multiple: number
}

export interface SignalStats {
  wins: number
  losses: number
  scratches: number
  total: number
  win_rate: number
}

export interface TimelineDay {
  date: string
  wins: number
  losses: number
  scratches: number
  win_rate: number
  avg_r: number
}

export interface PerformanceData {
  days: number
  total_picks: number
  graded_snapshots: number
  wins: number
  losses: number
  scratches: number
  ambiguous: number
  win_rate: number
  avg_r_multiple: number
  by_signal: Record<string, SignalStats>
  by_trend: Record<string, SignalStats>
  best_picks: PickGrading[]
  worst_picks: PickGrading[]
  timeline: TimelineDay[]
}

export interface ScoringWeights {
  weights: Record<string, number>
  description: string
  version: string | null
}

export interface ConfigVersion {
  version_id: string
  timestamp: string
  description: string
  content?: Record<string, unknown>
}

export interface VersionDiff {
  version_a: string
  version_b: string
  changes: { key: string; old: unknown; new: unknown }[]
}
