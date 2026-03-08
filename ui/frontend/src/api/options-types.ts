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
  sweep_analysis: string | null
  smart_money_analysis: string | null
  gex_analysis: string | null
  dark_pool_analysis: string | null
  iv_analysis: string | null
}

export interface OptionsFlowEnhanced extends OptionsFlowFull {
  news_headlines: NewsHeadline[]
  section_analyses: SectionAnalyses
}

// ── V3 Types ──────────────────────────────────────────────────

export interface FlowAlert {
  timestamp: string
  symbol: string
  strike: number | null
  expiry: string
  type: 'sweep' | 'block' | 'golden_sweep' | 'trade'
  side: string
  premium: number
  size: number
  ask_side_pct: number | null
  sentiment: 'bullish' | 'bearish' | 'neutral'
}

export interface DarkPoolPrint {
  timestamp: string
  price: number
  size: number
  notional: number
  exchange: string
}

export interface InstitutionalTrade {
  date: string
  name: string
  type: string
  amount: string
  shares: number
}

export interface FlowInterval {
  timestamp: string
  call_premium: number
  put_premium: number
  net_premium: number
}

export interface UnusualActivity {
  available: boolean
  sweep_count: number
  block_count: number
  golden_sweep_count: number
  total_sweep_premium: number
  dominant_side: string
  largest_sweep: FlowAlert | null
  volume_oi_flags: { strike: number; volume: number; oi: number; ratio: number }[]
}

export interface SmartMoneyFlow {
  available: boolean
  smart_money_pct: number
  retail_pct: number
  smart_money_sentiment: string
  retail_sentiment: string
  divergence_score: number
  smart_money_count?: number
  retail_count?: number
}

export interface ConvictionFactor {
  name: string
  score: number
  weight: number
  adjusted_weight: number
  available: boolean
  source: string
  detail: string
}

export interface ConvictionV2 {
  score: number
  label: string
  confidence: 'high' | 'medium' | 'low'
  factors: ConvictionFactor[]
  available_factors: number
  total_factors: number
}

export interface IVAnalysis {
  current_iv: number
  iv_percentile: number | null
  iv_skew: number
  avg_call_iv: number
  avg_put_iv: number
  term_structure: 'normal' | 'inverted' | 'contango'
  near_term_iv: number
  far_term_iv: number
  crush_risk: boolean
}

export interface GEXStrike {
  strike: number
  gex: number
}

export interface AdvancedGreeks {
  total_gex: number
  total_dex: number
  gex_flip_level: number | null
  gex_regime: 'positive' | 'negative'
  gex_description: string
  gex_by_strike: GEXStrike[]
}

export interface DPCorrelation {
  total_prints: number
  total_notional: number
  above_spot: number
  below_spot: number
  dp_sentiment: string
  avg_dp_price: number
  price_vs_spot_pct: number
}

export interface FlowMomentum {
  cp_momentum: string
  intraday_trend: string | null
}

export interface HistoricalIVPoint {
  date: string
  avg_iv: number
  min_iv: number
  max_iv: number
}

export interface ProviderStatus {
  yfinance: boolean
  unusual_whales: boolean
  alpha_vantage: boolean
}

export interface OptionsFlowV2 extends OptionsFlowEnhanced {
  flow_alerts: FlowAlert[] | null
  dark_pool: DarkPoolPrint[] | null
  institutional: { trades: InstitutionalTrade[] } | null
  flow_intervals: FlowInterval[] | null
  historical_iv: HistoricalIVPoint[] | null
  unusual_activity: UnusualActivity
  smart_money: SmartMoneyFlow
  conviction_v2: ConvictionV2
  iv_analysis: IVAnalysis | null
  advanced_greeks: AdvancedGreeks | null
  dp_correlation: DPCorrelation | null
  flow_momentum: FlowMomentum
  provider_status: ProviderStatus
}

export interface FlowAlertsResponse {
  symbol: string
  alerts: FlowAlert[]
  count: number
}
