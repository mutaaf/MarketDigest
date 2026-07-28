// Signal Forge type definitions

export interface PositionSize {
  units: number
  dollar_risk: number
  dollar_reward: number
  label: string
}

export interface OptionDetails {
  strategy: string
  strike: number
  expiry: string
  dte: number
  iv: number | null
  delta: number | null
  theta: number | null
  iv_rank: number | null
}

export interface Signal {
  id: string
  timestamp: string
  symbol: string
  name: string
  asset_type: 'forex' | 'equity' | 'option'
  direction: 'BUY' | 'SELL'
  confluence_score: number
  grade: string
  entry_price: number
  stop_loss: number
  target_1: number
  target_2: number
  risk_reward: number
  position_size?: PositionSize
  indicators: Record<string, any>
  explanation: string
  pine_strategy: string | null
  strategy_name?: string
  regime?: string
  conditions_met?: string[]
  ai_explanation?: string
  ai_timestamp?: string
  ai_age_label?: string
  ai_freshness?: 'fresh' | 'stale' | 'expired' | ''
  timing?: {
    hold_duration: string
    time_horizon: string
    best_entry_window: string
    time_stop_bars: number
    urgency: string
    when_to_exit: string
  }
  option_details?: OptionDetails
  status: string
}

export interface BacktestResult {
  symbol: string
  asset_type: string
  lookback_months: number
  start_balance: number
  final_balance: number
  total_return_pct: number
  total_trades: number
  wins: number
  losses: number
  win_rate: number
  avg_r_multiple: number
  profit_factor: number | string
  max_drawdown_pct: number
  passes_gate: boolean
  gate_requirements: Record<string, any>
  equity_curve: Array<{ date: string; equity: number }>
  trades: Array<BacktestTrade>
}

export interface BacktestTrade {
  date: string
  direction: string
  entry: number
  exit: number
  target: number
  stop: number
  pnl: number
  outcome: 'win' | 'loss'
  r_multiple: number
}

export interface RiskDashboardData {
  forex: AccountRisk
  options: AccountRisk
  portfolio: PortfolioRisk
}

export interface AccountRisk {
  account_balance: number
  daily_pnl: number
  daily_limit: number
  daily_risk_used_pct: number
  open_positions: number
  max_positions: number
  max_risk_per_trade: number
  trading_paused: boolean
}

export interface PortfolioRisk {
  total_balance: number
  total_daily_pnl: number
  total_positions: number
  total_risk_pct: number
}

export interface PaperPortfolio {
  forex: PaperAccount
  options: PaperAccount
  ready_for_live: boolean
}

export interface PaperAccount {
  balance: number
  initial_balance: number
  open_trades: PaperTrade[]
  stats: PaperStats
  return_pct: number
}

export interface PaperTrade {
  id: string
  symbol: string
  name: string
  asset_type: string
  direction: string
  entry_price: number
  stop_loss: number
  target_1: number
  target_2: number
  risk_reward: number
  dollar_risk: number
  position_size: string
  entry_time: string
  status: string
  confluence_score: number
  grade: string
}

export interface PaperStats {
  total_trades: number
  wins: number
  losses: number
  total_pnl: number
  win_rate: number
  avg_pnl: number
}

export interface JournalEntry {
  id: string
  symbol: string
  direction: string
  entry_price: number
  exit_price: number
  entry_time: string
  exit_time: string
  exit_reason: string
  pnl: number
  r_multiple: number
  outcome: string
}

export interface PineStrategy {
  id: string
  name: string
  description: string
}
