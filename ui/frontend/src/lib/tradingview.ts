/**
 * TradingView URL generator — maps symbols and indicators to TradingView chart URLs.
 *
 * URL format: https://www.tradingview.com/chart/?symbol=EXCHANGE:SYMBOL&interval=D
 * Studies format: &studies=StudyName@tv-basicstudies
 */

// Symbol → TradingView exchange:symbol mapping
const TV_SYMBOL_MAP: Record<string, string> = {
  // Forex
  USDJPY: 'FX:USDJPY',
  EURUSD: 'FX:EURUSD',
  GBPUSD: 'FX:GBPUSD',
  AUDUSD: 'FX:AUDUSD',
  USDCAD: 'FX:USDCAD',
  USDCHF: 'FX:USDCHF',
  NZDUSD: 'FX:NZDUSD',
  // ETFs
  SPY: 'AMEX:SPY',
  QQQ: 'NASDAQ:QQQ',
  IWM: 'AMEX:IWM',
  DIA: 'AMEX:DIA',
  // Stocks
  AAPL: 'NASDAQ:AAPL',
  MSFT: 'NASDAQ:MSFT',
  NVDA: 'NASDAQ:NVDA',
  TSLA: 'NASDAQ:TSLA',
  META: 'NASDAQ:META',
  AMZN: 'NASDAQ:AMZN',
  GOOGL: 'NASDAQ:GOOGL',
  AMD: 'NASDAQ:AMD',
  NFLX: 'NASDAQ:NFLX',
  JPM: 'NYSE:JPM',
  V: 'NYSE:V',
  BA: 'NYSE:BA',
}

// Indicator → TradingView study ID
const TV_STUDY_MAP: Record<string, string> = {
  rsi: 'RSI@tv-basicstudies',
  macd: 'MACD@tv-basicstudies',
  bollinger: 'BB@tv-basicstudies',
  stochastic: 'Stochastic@tv-basicstudies',
  ema_cross: 'MAExp@tv-basicstudies',
  adx: 'ADX@tv-basicstudies',
  atr: 'ATR@tv-basicstudies',
  volume: 'Volume@tv-basicstudies',
  pivot: 'PivotPointsStandard@tv-basicstudies',
  iv_rank: 'IVRank@tv-basicstudies',
  donchian: 'DONCH@tv-basicstudies',
}

// Strategy → recommended TradingView studies combo
const STRATEGY_STUDIES: Record<string, string[]> = {
  'EMA Trend Follow': ['MAExp@tv-basicstudies', 'RSI@tv-basicstudies', 'ADX@tv-basicstudies'],
  'BB Mean Reversion': ['BB@tv-basicstudies', 'RSI@tv-basicstudies', 'Stochastic@tv-basicstudies'],
  'Donchian Breakout': ['DONCH@tv-basicstudies', 'BB@tv-basicstudies', 'Volume@tv-basicstudies'],
  'RSI Momentum': ['RSI@tv-basicstudies', 'MACD@tv-basicstudies', 'MASimple@tv-basicstudies'],
  'Pivot Bounce': ['PivotPointsStandard@tv-basicstudies', 'RSI@tv-basicstudies'],
  'IV Premium Sell': ['RSI@tv-basicstudies', 'BB@tv-basicstudies'],
  'Range Breakout': ['BB@tv-basicstudies', 'Volume@tv-basicstudies', 'ATR@tv-basicstudies'],
  'Swing Reversal': ['RSI@tv-basicstudies', 'MACD@tv-basicstudies', 'Volume@tv-basicstudies'],
  'MACD Divergence': ['MACD@tv-basicstudies', 'RSI@tv-basicstudies'],
  'Volatility Squeeze': ['BB@tv-basicstudies', 'MACD@tv-basicstudies', 'ATR@tv-basicstudies'],
}

const BASE_URL = 'https://www.tradingview.com/chart/'

/**
 * Get TradingView chart URL for a symbol
 */
export function getTVChartUrl(symbol: string, interval: string = 'D'): string {
  const tvSymbol = TV_SYMBOL_MAP[symbol] || symbol
  return `${BASE_URL}?symbol=${tvSymbol}&interval=${interval}`
}

/**
 * Get TradingView chart URL with a specific indicator overlay
 */
export function getTVIndicatorUrl(symbol: string, indicator: string, interval: string = 'D'): string {
  const tvSymbol = TV_SYMBOL_MAP[symbol] || symbol
  const study = TV_STUDY_MAP[indicator]
  if (!study) return getTVChartUrl(symbol, interval)
  return `${BASE_URL}?symbol=${tvSymbol}&interval=${interval}&studies=${encodeURIComponent(study)}`
}

/**
 * Get TradingView chart URL with all indicators for a strategy
 */
export function getTVStrategyUrl(symbol: string, strategyName: string, interval: string = 'D'): string {
  const tvSymbol = TV_SYMBOL_MAP[symbol] || symbol
  const studies = STRATEGY_STUDIES[strategyName]
  if (!studies || studies.length === 0) return getTVChartUrl(symbol, interval)
  const studiesParam = studies.join('%1F')
  return `${BASE_URL}?symbol=${tvSymbol}&interval=${interval}&studies=${encodeURIComponent(studiesParam)}`
}

/**
 * Get a human-readable indicator label for display
 */
export function getIndicatorLabel(key: string): string {
  const labels: Record<string, string> = {
    rsi: 'RSI (14)',
    macd: 'MACD (12/26/9)',
    bollinger: 'Bollinger Bands',
    stochastic: 'Stochastic (14,3)',
    ema_cross: 'EMA 9/21',
    adx: 'ADX (14)',
    atr: 'ATR (14)',
    pivot: 'Pivot Points',
    iv_rank: 'IV Rank',
    volume: 'Volume',
    donchian: 'Donchian Channel',
  }
  return labels[key] || key.replace('_', ' ')
}

/**
 * Check if we have a TradingView mapping for this symbol
 */
export function hasTVMapping(symbol: string): boolean {
  return symbol in TV_SYMBOL_MAP
}
