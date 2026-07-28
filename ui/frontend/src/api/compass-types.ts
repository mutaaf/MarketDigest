// Compass (long-term investing) API types

export interface PortfolioListItem {
  name: string
  slug: string
  holdings_count: number
  cash: number
  updated: string | null
}

export interface ValuedHolding {
  symbol: string
  shares: number
  cost_basis: number
  account: string
  price: number | null
  value: number | null
  day_change_pct: number | null
  day_change?: number
  gain: number | null
  gain_pct: number | null
}

export interface Valuation {
  holdings: ValuedHolding[]
  cash: number
  total_value: number
  invested_value: number
  total_cost: number | null
  total_gain: number | null
  total_gain_pct: number | null
  day_change: number
  day_change_pct: number
  warnings: string[]
}

export interface AllocationSlice {
  key: string
  label: string
  value: number
  weight: number
}

export interface AllocationHolding extends ValuedHolding {
  weight: number
  asset_class: string
  instrument_type: string
  display_name?: string
}

export interface Allocation {
  asset_classes: AllocationSlice[]
  sectors: AllocationSlice[]
  by_holding: AllocationHolding[]
  weighted_expense_ratio: number | null
  unclassified: string[]
}

export interface HealthFactor {
  name: string
  score: number
  status: 'good' | 'ok' | 'warn'
  detail: string
}

export interface Health {
  grade: string | null
  score: number | null
  factors: HealthFactor[]
  summary: string
}

export interface PortfolioSummary {
  name: string
  valuation: Valuation
  allocation: Allocation
  health: Health
  targets: Record<string, number>
}

export interface Recommendation {
  symbol: string
  name: string
  type: 'etf' | 'stock'
  asset_class: string
  sector?: string
  grade: string
  score: number
  risk_level?: string
  expense_ratio?: number | null
  dividend_yield?: number | null
  return_5y?: number | null
  reasons: string[]
}

export interface Recommendations {
  recommendations: Recommendation[]
  gaps: { asset_class: string; target: number; actual: number; gap: number }[]
  cash_available: number
  warnings: string[]
  generated_at: string
  targets_are_default: boolean
  note?: string
}

export interface CompareSide {
  symbol: string
  name: string
  type: 'etf' | 'stock'
  grade: string
  score: number
  risk_level?: string
  sector?: string
  sub_scores: Record<string, number | null>
  metrics: Record<string, number | null>
  top_holdings?: { symbol: string; name: string; weight: number }[]
}

export interface CompareResult {
  a: CompareSide
  b: CompareSide
  verdict: string
}

export interface SearchResult {
  symbol: string
  name: string
  type: 'etf' | 'stock'
  asset_class?: string
  category?: string
}
