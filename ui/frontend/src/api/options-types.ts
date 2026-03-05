export interface ExpiryDistribution {
  expiry: string
  days_to_expiry: number
  call_premium: number
  put_premium: number
  total_premium: number
  pct_of_total: number
  top_strike: number | null
  cp_ratio: number
}

export interface StrikeHeatmapEntry {
  strike: number
  call_premium: number
  put_premium: number
  call_oi: number
  put_oi: number
  net_premium: number
}

export interface GreeksSummary {
  net_delta: number
  total_gamma: number
  put_wall: number | null
  call_wall: number | null
  max_pain: number | null
}

export interface OIAnalysis {
  total_call_oi: number
  total_put_oi: number
  pcr_oi: number
  put_wall: number | null
  call_wall: number | null
}

export interface DailyFlowBreakdown {
  day: string
  date: string
  total_call_premium: number
  total_put_premium: number
  total_premium: number
  cp_ratio: number
  sentiment: string
}

export interface OptionsFlowFull {
  symbol: string
  stock_price: number
  fetched_at: string
  total_call_premium: number
  total_put_premium: number
  total_premium: number
  cp_ratio: number
  conviction: string
  conviction_score: number
  top_call_strike: number | null
  top_put_strike: number | null
  expiry_distribution: ExpiryDistribution[]
  strike_heatmap: StrikeHeatmapEntry[]
  greeks_summary: GreeksSummary
  oi_analysis: OIAnalysis
  daily_breakdown: DailyFlowBreakdown[]
  arc_status: string
  arc_reading: string | null
}

export interface OptionsEligibleSymbol {
  symbol: string
  name: string
}

export interface NewsHeadline {
  title: string
  description: string
  url: string | null
  source: string | null
  published_at: string | null
}

export interface SectionAnalyses {
  flow_summary: string | null
  premium_analysis: string | null
  greeks_analysis: string | null
  expiry_analysis: string | null
  strike_analysis: string | null
  news_correlation: string | null
  action_items: string | null
}

export interface OptionsFlowEnhanced extends OptionsFlowFull {
  news_headlines: NewsHeadline[]
  section_analyses: SectionAnalyses
}
