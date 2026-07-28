import { useState, useEffect, useCallback, useRef } from 'react'
import api from '../api/client'
import type { Signal, RiskDashboardData } from '../api/signals-types'
import { getTVChartUrl, getTVIndicatorUrl, getTVStrategyUrl, getIndicatorLabel } from '../lib/tradingview'

/** Rate a signal as TAKE / WATCH / SKIP */
function rateSignal(s: Signal): 'TAKE' | 'WATCH' | 'SKIP' {
  const score = s.confluence_score
  const rr = s.risk_reward
  const conds = s.conditions_met?.length || 0
  if (rr < 1.5 || score < 40) return 'SKIP'
  if ((score >= 65 && rr >= 2.0 && conds >= 3) || (score >= 70 && rr >= 1.8) || score >= 80) return 'TAKE'
  if (score >= 50 || (rr >= 2.0 && conds >= 2)) return 'WATCH'
  return 'SKIP'
}

const ratingStyle = {
  TAKE: 'bg-green-500/20 text-green-400 border-green-500/30',
  WATCH: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  SKIP: 'bg-gray-700/50 text-gray-500 border-gray-700',
}

/** Clickable link that opens TradingView in a new tab */
function TVLink({ href, children, className = '' }: { href: string, children: React.ReactNode, className?: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      className={`cursor-pointer hover:underline decoration-dotted underline-offset-2 ${className}`}
      title="Open in TradingView"
    >{children}</a>
  )
}

const gradeColors: Record<string, string> = {
  'A+': 'text-green-400', 'A': 'text-green-400', 'A-': 'text-green-400',
  'B+': 'text-emerald-400', 'B': 'text-emerald-400', 'B-': 'text-emerald-400',
  'C+': 'text-yellow-400', 'C': 'text-yellow-400', 'C-': 'text-yellow-400',
  'D': 'text-orange-400', 'F': 'text-red-400',
}

const gradeBg: Record<string, string> = {
  'A+': 'bg-green-500/20', 'A': 'bg-green-500/20', 'A-': 'bg-green-500/20',
  'B+': 'bg-emerald-500/20', 'B': 'bg-emerald-500/20', 'B-': 'bg-emerald-500/20',
  'C+': 'bg-yellow-500/15', 'C': 'bg-yellow-500/15', 'C-': 'bg-yellow-500/15',
  'D': 'bg-orange-500/15', 'F': 'bg-red-500/15',
}

function ConfluenceBar({ score, label, weight, tvUrl }: { score: number, label: string, weight: string, tvUrl?: string }) {
  const color = score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-emerald-500' : score >= 40 ? 'bg-yellow-500' : 'bg-red-500'
  const inner = (
    <div className={`flex items-center gap-2 text-xs ${tvUrl ? 'hover:bg-gray-800 rounded px-1 -mx-1 cursor-pointer' : ''}`}>
      <span className={`w-20 text-gray-500 truncate ${tvUrl ? 'group-hover:text-blue-400' : ''}`}>{label}</span>
      <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="w-8 text-right text-gray-400 font-mono">{score.toFixed(0)}</span>
      <span className="w-8 text-right text-gray-600 font-mono text-[10px]">{weight}</span>
    </div>
  )
  if (tvUrl) {
    return <a href={tvUrl} target="_blank" rel="noopener noreferrer" className="group block">{inner}</a>
  }
  return inner
}

function SignalDetail({ signal, onPaperTrade, onClose }: {
  signal: Signal, onPaperTrade: (s: Signal) => void, onClose: () => void
}) {
  const [aiExplanation, setAiExplanation] = useState(signal.ai_explanation || '')
  const [aiFreshness, setAiFreshness] = useState<string>(signal.ai_freshness || '')
  const [aiAge, setAiAge] = useState(signal.ai_age_label || '')
  const [aiLoading, setAiLoading] = useState(false)

  // Load cached explanation or auto-fetch when signal changes
  useEffect(() => {
    if (signal.ai_explanation) {
      setAiExplanation(signal.ai_explanation)
      setAiFreshness(signal.ai_freshness || 'fresh')
      setAiAge(signal.ai_age_label || '')

      // Auto-refresh if expired
      if (signal.ai_freshness === 'expired') {
        fetchAI(true)
      }
    } else {
      setAiExplanation('')
      setAiFreshness('')
      setAiAge('')
      // Auto-fetch for TAKE/WATCH signals
      const rating = rateSignal(signal)
      if (rating === 'TAKE' || rating === 'WATCH') {
        fetchAI(false)
      }
    }
  }, [signal.id])

  const fetchAI = async (force: boolean = false) => {
    setAiLoading(true)
    try {
      const res = await api.post(`/signals/analyze?force=${force}`, signal)
      setAiExplanation(res.data.explanation || '')
      setAiFreshness(res.data.freshness || 'fresh')
      setAiAge(res.data.age_label || 'just now')
    } catch {
      setAiExplanation('Failed to load AI analysis. Check API keys in Settings.')
      setAiFreshness('error')
    } finally {
      setAiLoading(false)
    }
  }

  const isBuy = signal.direction === 'BUY'
  const components = signal.indicators?.components || {}
  const gradeColor = gradeColors[signal.grade] || 'text-gray-400'

  // Build indicator summary
  const indicatorItems = []
  const rsi = signal.indicators?.rsi
  if (rsi != null) indicatorItems.push({ label: 'RSI', value: `${rsi.toFixed(1)}`, color: rsi < 30 ? 'text-green-400' : rsi > 70 ? 'text-red-400' : 'text-gray-300' })
  const ema = signal.indicators?.ema_cross
  if (ema) indicatorItems.push({ label: 'EMA 9/21', value: ema.signal?.replace('_', ' '), color: ema.signal?.includes('bullish') ? 'text-green-400' : ema.signal?.includes('bearish') ? 'text-red-400' : 'text-gray-400' })
  const macd = signal.indicators?.macd
  if (macd) indicatorItems.push({ label: 'MACD', value: macd.histogram > 0 ? `+${macd.histogram.toFixed(4)}` : macd.histogram.toFixed(4), color: macd.histogram > 0 ? 'text-green-400' : 'text-red-400' })
  const stoch = signal.indicators?.stochastic
  if (stoch) indicatorItems.push({ label: 'Stochastic', value: `K:${stoch.k} D:${stoch.d || '-'}`, color: stoch.k < 20 ? 'text-green-400' : stoch.k > 80 ? 'text-red-400' : 'text-gray-300' })
  const bb = signal.indicators?.bollinger
  if (bb) indicatorItems.push({ label: 'BB %B', value: `${(bb.pct_b * 100).toFixed(0)}%`, color: bb.pct_b < 0.2 ? 'text-green-400' : bb.pct_b > 0.8 ? 'text-red-400' : 'text-gray-300' })
  const ivRank = signal.indicators?.iv_rank
  if (ivRank != null) indicatorItems.push({ label: 'IV Rank', value: `${ivRank.toFixed(0)}%`, color: ivRank < 30 ? 'text-green-400' : ivRank > 70 ? 'text-red-400' : 'text-gray-300' })

  const isSpec = signal.confluence_score < 65

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className={`px-5 py-4 ${isBuy ? 'bg-green-500/5 border-b border-green-500/20' : 'bg-red-500/5 border-b border-red-500/20'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`text-2xl font-black ${isBuy ? 'text-green-400' : 'text-red-400'}`}>
              {isBuy ? '\u25B2' : '\u25BC'} {signal.direction}
            </div>
            <div>
              <TVLink href={getTVStrategyUrl(signal.symbol, signal.strategy_name || '', 'D')}
                className="text-xl font-bold text-white font-mono hover:text-blue-400 transition-colors">
                {signal.symbol}
              </TVLink>
              <div className="text-xs text-gray-500">{signal.name}</div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className={`text-3xl font-black font-mono ${gradeColor}`}>{signal.grade}</div>
              <div className="text-xs text-gray-500">{signal.confluence_score.toFixed(0)}/100</div>
            </div>
            <button onClick={onClose} className="text-gray-600 hover:text-gray-400 text-xl">x</button>
          </div>
        </div>
        {/* Strategy & Regime */}
        <div className="mt-2 flex items-center gap-2">
          {signal.strategy_name && (
            <span className="text-xs px-2 py-1 rounded bg-cyan-500/15 text-cyan-400 font-medium border border-cyan-500/20">
              {signal.strategy_name}
            </span>
          )}
          {signal.regime && (
            <span className="text-xs px-2 py-1 rounded bg-gray-700 text-gray-300">
              {signal.regime.replace('_', ' ').toUpperCase()}
            </span>
          )}
        </div>
        {isSpec && (
          <div className="mt-2 px-2 py-1 bg-yellow-500/10 border border-yellow-500/20 rounded text-xs text-yellow-400">
            Speculative signal — below B- grade. Higher risk, use smaller position or skip.
          </div>
        )}
        {/* Conditions Met */}
        {signal.conditions_met && signal.conditions_met.length > 0 && (
          <div className="mt-2 space-y-1">
            {signal.conditions_met.map((c, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className="text-green-400">&#10003;</span>
                <span className="text-gray-300">{c}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Timing Bar */}
      {signal.timing && (
        <div className="px-5 py-3 bg-gray-800/30 border-b border-gray-800 grid grid-cols-4 gap-4 text-xs">
          <div>
            <span className="text-gray-600 uppercase text-[9px]">Hold Time</span>
            <div className="text-white font-medium mt-0.5">{signal.timing.hold_duration}</div>
          </div>
          <div>
            <span className="text-gray-600 uppercase text-[9px]">Horizon</span>
            <div className="mt-0.5">
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                signal.timing.time_horizon === 'position' ? 'bg-blue-500/20 text-blue-400' :
                signal.timing.time_horizon.includes('swing') ? 'bg-purple-500/20 text-purple-400' :
                'bg-amber-500/20 text-amber-400'
              }`}>
                {signal.timing.time_horizon.toUpperCase()}
              </span>
            </div>
          </div>
          <div>
            <span className="text-gray-600 uppercase text-[9px]">Urgency</span>
            <div className="text-amber-400 font-medium mt-0.5">{signal.timing.urgency}</div>
          </div>
          <div>
            <span className="text-gray-600 uppercase text-[9px]">When to Enter</span>
            <div className="text-gray-300 mt-0.5">{signal.timing.best_entry_window}</div>
          </div>
        </div>
      )}

      {/* Exit Instructions */}
      {signal.timing?.when_to_exit && (
        <div className="px-5 py-2 bg-green-900/10 border-b border-green-500/10">
          <span className="text-[9px] text-green-500 uppercase font-bold">Exit Plan: </span>
          <span className="text-xs text-green-300/80">{signal.timing.when_to_exit}</span>
        </div>
      )}

      <div className="p-5 grid grid-cols-3 gap-6">
        {/* Left — Trade Levels */}
        <div>
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Trade Levels</h3>
          <div className="space-y-3">
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-[10px] text-gray-500 uppercase">Entry</div>
              <div className="text-lg font-bold font-mono text-white">{signal.entry_price}</div>
            </div>
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <div className="text-[10px] text-red-400 uppercase">Stop Loss</div>
              <div className="text-lg font-bold font-mono text-red-300">{signal.stop_loss}</div>
              <div className="text-[10px] text-red-400/60">
                {signal.position_size ? `Risk: $${signal.position_size.dollar_risk}` : ''}
              </div>
            </div>
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
              <div className="text-[10px] text-green-400 uppercase">Target 1 (2R)</div>
              <div className="text-lg font-bold font-mono text-green-300">{signal.target_1}</div>
              <div className="text-[10px] text-green-400/60">
                {signal.position_size ? `Reward: $${signal.position_size.dollar_reward}` : ''}
              </div>
            </div>
            <div className="bg-green-500/5 border border-green-500/10 rounded-lg p-3">
              <div className="text-[10px] text-green-400/70 uppercase">Target 2 (3R)</div>
              <div className="text-lg font-bold font-mono text-green-200">{signal.target_2}</div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2 text-center">
            <div className="bg-amber-500/10 rounded-lg p-2">
              <div className="text-[10px] text-amber-400">Risk/Reward</div>
              <div className="text-lg font-bold font-mono text-amber-300">{signal.risk_reward}:1</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-2">
              <div className="text-[10px] text-gray-500">Position</div>
              <div className="text-sm font-bold font-mono text-white">{signal.position_size?.label || '-'}</div>
            </div>
          </div>
        </div>

        {/* Middle — Indicators */}
        <div>
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">
            Indicators
            <span className="text-[9px] text-gray-700 font-normal ml-2">click to view on TradingView</span>
          </h3>
          <div className="space-y-2 mb-4">
            {indicatorItems.map((item, i) => {
              const indicatorKey = item.label.toLowerCase().replace(/[^a-z]/g, '').replace('ema921', 'ema_cross').replace('stochastic', 'stochastic').replace('bollinger', 'bollinger').replace('macd', 'macd').replace('rsi', 'rsi').replace('bb', 'bollinger').replace('ivrank', 'iv_rank')
              const tvUrl = getTVIndicatorUrl(signal.symbol, indicatorKey, 'D')
              return (
                <a key={i} href={tvUrl} target="_blank" rel="noopener noreferrer"
                  className="flex items-center justify-between bg-gray-800 rounded px-3 py-2 hover:bg-gray-700 transition-colors cursor-pointer group"
                  title={`View ${item.label} for ${signal.symbol} on TradingView`}
                >
                  <span className="text-xs text-gray-500 group-hover:text-blue-400 transition-colors flex items-center gap-1">
                    {item.label}
                    <svg className="w-3 h-3 text-gray-700 group-hover:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                  </span>
                  <span className={`text-sm font-mono font-bold ${item.color}`}>{item.value}</span>
                </a>
              )
            })}
          </div>

          {signal.option_details && (
            <>
              <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 mt-4">Option Details</h3>
              <div className="space-y-2">
                <div className="flex justify-between bg-gray-800 rounded px-3 py-2">
                  <span className="text-xs text-gray-500">Strategy</span>
                  <span className="text-sm font-mono text-purple-300">{signal.option_details.strategy.replace('_', ' ')}</span>
                </div>
                <div className="flex justify-between bg-gray-800 rounded px-3 py-2">
                  <span className="text-xs text-gray-500">Strike</span>
                  <span className="text-sm font-mono text-white">${signal.option_details.strike}</span>
                </div>
                <div className="flex justify-between bg-gray-800 rounded px-3 py-2">
                  <span className="text-xs text-gray-500">DTE</span>
                  <span className="text-sm font-mono text-white">{signal.option_details.dte} days</span>
                </div>
                {signal.option_details.iv_rank != null && (
                  <div className="flex justify-between bg-gray-800 rounded px-3 py-2">
                    <span className="text-xs text-gray-500">IV Rank</span>
                    <span className={`text-sm font-mono ${signal.option_details.iv_rank < 30 ? 'text-green-400' : signal.option_details.iv_rank > 70 ? 'text-red-400' : 'text-white'}`}>
                      {signal.option_details.iv_rank.toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Right — Confluence Breakdown */}
        <div>
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Confluence Breakdown</h3>
          <div className="space-y-2">
            {Object.entries(components).map(([key, score]) => {
              const weightMap: Record<string, string> = {
                ema_cross: '20%', rsi: '20%', bollinger: '15%', stochastic: '15%',
                macd: '10%', pivot: '15%', atr_filter: '5%', iv_rank: '20%', greeks: '15%',
              }
              const tvKey = key === 'atr_filter' ? 'atr' : key
              return (
                <ConfluenceBar
                  key={key}
                  label={key.replace('_', ' ')}
                  score={score as number}
                  weight={weightMap[key] || ''}
                  tvUrl={getTVIndicatorUrl(signal.symbol, tvKey, 'D')}
                />
              )
            })}
          </div>

          {/* AI Analysis */}
          <div className={`mt-4 rounded-lg p-4 border ${
            aiFreshness === 'fresh' ? 'bg-gradient-to-br from-blue-900/20 to-purple-900/20 border-blue-500/20' :
            aiFreshness === 'stale' ? 'bg-gradient-to-br from-amber-900/10 to-gray-900/20 border-amber-500/20' :
            'bg-gray-800/50 border-gray-700'
          }`}>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${
                  aiFreshness === 'fresh' ? 'bg-green-400' :
                  aiFreshness === 'stale' ? 'bg-amber-400' :
                  aiExplanation ? 'bg-red-400' : 'bg-gray-600'
                }`}></span>
                AI Analysis
                {/* Freshness badge */}
                {aiAge && (
                  <span className={`text-[9px] font-normal px-1.5 py-0.5 rounded ${
                    aiFreshness === 'fresh' ? 'bg-green-500/15 text-green-400' :
                    aiFreshness === 'stale' ? 'bg-amber-500/15 text-amber-400' :
                    'bg-red-500/15 text-red-400'
                  }`}>
                    {aiAge}
                    {aiFreshness === 'stale' && ' \u00B7 stale'}
                    {aiFreshness === 'expired' && ' \u00B7 expired'}
                  </span>
                )}
              </h4>
              <div className="flex items-center gap-2">
                {!aiExplanation && !aiLoading && (
                  <button
                    onClick={() => fetchAI(false)}
                    className="text-xs px-3 py-1 rounded bg-blue-600/30 text-blue-300 hover:bg-blue-600/50 transition-colors"
                  >
                    Get AI Insight
                  </button>
                )}
                {aiExplanation && (
                  <button
                    onClick={() => fetchAI(true)}
                    disabled={aiLoading}
                    className={`text-[10px] px-2 py-1 rounded flex items-center gap-1 transition-colors ${
                      aiFreshness === 'stale' || aiFreshness === 'expired'
                        ? 'bg-amber-600/20 text-amber-400 hover:bg-amber-600/40'
                        : 'bg-gray-700 text-gray-500 hover:text-gray-300'
                    }`}
                    title="Regenerate with latest market data and news"
                  >
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    {aiLoading ? 'Refreshing...' : aiFreshness === 'stale' || aiFreshness === 'expired' ? 'Refresh (stale)' : 'Refresh'}
                  </button>
                )}
              </div>
            </div>

            {/* Stale warning banner */}
            {aiFreshness === 'stale' && !aiLoading && (
              <div className="mb-2 px-2 py-1 rounded bg-amber-500/10 border border-amber-500/15 text-[10px] text-amber-400">
                This analysis is {aiAge} old. Market conditions may have changed. Click Refresh for updated analysis with current news.
              </div>
            )}
            {aiFreshness === 'expired' && !aiLoading && (
              <div className="mb-2 px-2 py-1 rounded bg-red-500/10 border border-red-500/15 text-[10px] text-red-400">
                This analysis has expired ({aiAge}). Auto-refreshing with current market data...
              </div>
            )}

            {aiLoading ? (
              <div className="flex items-center gap-2 py-3">
                <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                <span className="text-xs text-blue-300">
                  {aiExplanation ? 'Refreshing with latest news and market data...' : 'Generating AI analysis with market context...'}
                </span>
              </div>
            ) : aiExplanation ? (
              <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{aiExplanation}</p>
            ) : (
              <p className="text-xs text-gray-500 leading-relaxed">
                AI analysis auto-generates for TAKE and WATCH signals. Click "Get AI Insight" for SKIP signals.
              </p>
            )}

            {/* TTL legend */}
            {aiExplanation && (
              <div className="mt-3 flex items-center gap-3 text-[9px] text-gray-700">
                <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-green-400"></span> Fresh (&lt;30m)</span>
                <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span> Stale (30m-2h)</span>
                <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-red-400"></span> Expired (&gt;2h)</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action Bar */}
      <div className="px-5 py-3 bg-gray-800/50 border-t border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className={`px-2 py-0.5 rounded ${signal.asset_type === 'forex' ? 'bg-blue-400/20 text-blue-300' : 'bg-purple-400/20 text-purple-300'}`}>
            {signal.asset_type === 'forex' ? 'FOREX (Manual on TastyFX)' : 'OPTIONS (Tastytrade)'}
          </span>
          <span>{new Date(signal.timestamp).toLocaleTimeString()}</span>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={getTVStrategyUrl(signal.symbol, signal.strategy_name || '', 'D')}
            target="_blank" rel="noopener noreferrer"
            className="px-4 py-2 rounded-lg text-sm font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
            TradingView
          </a>
          <button
            onClick={() => onPaperTrade(signal)}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition-colors ${
              isBuy ? 'bg-green-600 hover:bg-green-500 text-white' : 'bg-red-600 hover:bg-red-500 text-white'
            }`}
          >
            Paper {signal.direction} {signal.symbol}
          </button>
        </div>
      </div>
    </div>
  )
}

function SignalRow({ signal, isSelected, onSelect }: {
  signal: Signal, isSelected: boolean, onSelect: (s: Signal) => void
}) {
  const isBuy = signal.direction === 'BUY'
  const gradeColor = gradeColors[signal.grade] || 'text-gray-400'
  const isSpec = signal.confluence_score < 65
  const rating = rateSignal(signal)

  return (
    <button
      onClick={() => onSelect(signal)}
      className={`w-full text-left px-4 py-3 border-b border-gray-800 hover:bg-gray-800/50 transition-colors flex items-center gap-3 ${
        isSelected ? 'bg-gray-800/80 border-l-2 border-l-blue-500' : ''
      }`}
    >
      <div className={`text-lg font-black w-6 ${isBuy ? 'text-green-400' : 'text-red-400'}`}>
        {isBuy ? '\u25B2' : '\u25BC'}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <TVLink href={getTVStrategyUrl(signal.symbol, signal.strategy_name || '', 'D')}
            className="font-bold font-mono text-white hover:text-blue-400 transition-colors">
            {signal.symbol}
          </TVLink>
          <span className={`text-xs px-1.5 py-0.5 rounded ${signal.asset_type === 'forex' ? 'bg-blue-400/15 text-blue-400' : 'bg-purple-400/15 text-purple-400'}`}>
            {signal.asset_type === 'forex' ? 'FX' : 'OPT'}
          </span>
          {isSpec && <span className="text-[10px] px-1 py-0.5 rounded bg-yellow-500/15 text-yellow-500">SPEC</span>}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          {signal.strategy_name && (
            <TVLink href={getTVStrategyUrl(signal.symbol, signal.strategy_name, 'D')}
              className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-400 font-medium hover:bg-cyan-500/25 transition-colors">
              {signal.strategy_name}
            </TVLink>
          )}
          {signal.regime && (
            <span className="text-[10px] text-gray-600">
              {signal.regime.replace('_', ' ')}
            </span>
          )}
        </div>
      </div>
      <div className="text-right flex flex-col items-end gap-0.5">
        <span className={`text-[10px] px-1.5 py-0.5 rounded border font-bold ${ratingStyle[rating]}`}>
          {rating === 'TAKE' ? '\u2713 ' : rating === 'WATCH' ? '\u25CB ' : ''}{rating}
        </span>
        <div className={`text-sm font-black font-mono ${gradeColor}`}>{signal.grade}</div>
      </div>
      <div className="text-right w-16">
        <div className="text-sm font-mono text-white">{signal.entry_price}</div>
        <div className="text-[10px] text-amber-400 font-mono">{signal.risk_reward}:1</div>
      </div>
    </button>
  )
}

function RiskGauge({ label, value, max, unit = '%' }: { label: string, value: number, max: number, unit?: string }) {
  const pct = Math.min((Math.abs(value) / max) * 100, 100)
  const color = pct > 75 ? 'bg-red-500' : pct > 50 ? 'bg-amber-500' : 'bg-green-500'
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-500">{label}</span>
        <span className="text-gray-300 font-mono">{value}{unit} / {max}{unit}</span>
      </div>
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function SignalTerminal() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [risk, setRisk] = useState<RiskDashboardData | null>(null)
  const [livePositions, setLivePositions] = useState<any[]>([])
  const [totalUnrealized, setTotalUnrealized] = useState(0)
  const [paperStats, setPaperStats] = useState<any>(null)
  const [scanning, setScanning] = useState(false)
  const [closingId, setClosingId] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [showPositions, setShowPositions] = useState(false)
  const [filter, setFilter] = useState<'all' | 'forex' | 'options'>('all')
  const [lastScan, setLastScan] = useState<string>('')
  const [marketCtx, setMarketCtx] = useState<any>(null)
  const [autopilot, setAutopilot] = useState<any>(null)
  const [apLoading, setApLoading] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchLatest = useCallback(async () => {
    try {
      const [sigRes, riskRes, posRes, paperRes] = await Promise.all([
        api.get('/signals/latest'),
        api.get('/risk/dashboard'),
        api.get('/trading/paper/positions'),
        api.get('/trading/paper/portfolio'),
      ])
      const sigs = sigRes.data.signals || []
      setSignals(sigs)
      setRisk(riskRes.data)
      setLivePositions(posRes.data.positions || [])
      setTotalUnrealized(posRes.data.total_unrealized_pnl || 0)
      setPaperStats({
        forex: paperRes.data?.forex?.stats,
        options: paperRes.data?.options?.stats,
        ready_for_live: paperRes.data?.ready_for_live,
      })
      if (sigs.length > 0) setLastScan(new Date().toLocaleTimeString())

      // Fetch market context + autopilot status
      try {
        const [ctxRes, apRes] = await Promise.all([
          api.get('/signals/market-context'),
          api.get('/signals/autopilot/status'),
        ])
        setMarketCtx(ctxRes.data)
        setAutopilot(apRes.data)
      } catch { /* ignore */ }
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    fetchLatest()
    // Auto-refresh every 60 seconds
    intervalRef.current = setInterval(fetchLatest, 60000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [fetchLatest])

  const runScan = async () => {
    setScanning(true)
    setMessage('')
    try {
      const res = await api.get('/signals/scan')
      const sigs = res.data.signals || []
      setSignals(sigs)
      setLastScan(new Date().toLocaleTimeString())
      const good = sigs.filter((s: Signal) => s.confluence_score >= 65).length
      const spec = sigs.filter((s: Signal) => s.confluence_score < 65).length
      setMessage(`${sigs.length} signals (${good} strong, ${spec} speculative)`)
      const riskRes = await api.get('/risk/dashboard')
      setRisk(riskRes.data)
    } catch (e: any) {
      setMessage(`Scan failed: ${e.response?.data?.detail || e.message}`)
    } finally {
      setScanning(false)
    }
  }

  const closeTrade = async (tradeId: string, symbol: string) => {
    setClosingId(tradeId)
    try {
      const res = await api.post(`/trading/paper/close-at-market?trade_id=${tradeId}`)
      const d = res.data
      setMessage(`Closed ${symbol}: ${d.outcome === 'win' ? '\u2705' : '\u274C'} ${d.outcome.toUpperCase()} | P&L: $${d.pnl >= 0 ? '+' : ''}${d.pnl} (${d.r_multiple >= 0 ? '+' : ''}${d.r_multiple}R)`)
      await fetchLatest()
    } catch (e: any) {
      setMessage(`\u274C Close failed: ${e.response?.data?.detail || e.message}`)
    } finally {
      setClosingId(null)
    }
  }

  const paperTrade = async (signal: Signal) => {
    try {
      const res = await api.post('/trading/paper/enter', {
        signal_id: signal.id,
        symbol: signal.symbol,
        direction: signal.direction,
        entry_price: signal.entry_price,
        stop_loss: signal.stop_loss,
        target_1: signal.target_1,
        asset_type: signal.asset_type,
      })
      setMessage(`\u2705 Paper ${signal.direction} ${signal.symbol} entered @ ${signal.entry_price} | Risk $${signal.position_size?.dollar_risk || '?'} | Target $${signal.position_size?.dollar_reward || '?'}`)
      // Immediately refresh portfolio to show the new position
      await fetchLatest()
    } catch (e: any) {
      setMessage(`\u274C ${e.response?.data?.detail || 'Paper trade failed'}`)
    }
  }

  const filteredSignals = signals.filter(s => {
    if (filter === 'forex') return s.asset_type === 'forex'
    if (filter === 'options') return s.asset_type !== 'forex'
    return true
  })

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      {/* Top Bar */}
      <div className="bg-gray-900 border-b border-gray-800 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sm font-bold text-gray-300">SIGNAL FORGE</span>
          {/* Autopilot Toggle */}
          <button
            onClick={async () => {
              setApLoading(true)
              try {
                if (autopilot?.running) {
                  await api.post('/signals/autopilot/stop')
                  setMessage('Autopilot stopped')
                } else {
                  await api.post('/signals/autopilot/start?interval=5')
                  setMessage('Autopilot started — scanning every 5 min, auto paper-trading TAKE signals, alerts via Telegram')
                }
                const res = await api.get('/signals/autopilot/status')
                setAutopilot(res.data)
              } catch (e: any) {
                setMessage(`Autopilot error: ${e.response?.data?.detail || e.message}`)
              } finally {
                setApLoading(false)
              }
            }}
            disabled={apLoading}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              autopilot?.running
                ? 'bg-green-600/20 text-green-400 border border-green-500/30 hover:bg-red-600/20 hover:text-red-400 hover:border-red-500/30'
                : 'bg-gray-800 text-gray-400 border border-gray-700 hover:bg-green-600/20 hover:text-green-400 hover:border-green-500/30'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${autopilot?.running ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
            {apLoading ? '...' : autopilot?.running ? 'AUTOPILOT ON' : 'AUTOPILOT OFF'}
          </button>
          {autopilot?.running && (
            <span className="text-[10px] text-gray-600">
              {autopilot.signals_today || 0} signals | {autopilot.trades_today || 0} trades today
            </span>
          )}
          <div className="flex gap-1 bg-gray-800 rounded-lg p-0.5">
            {(['all', 'forex', 'options'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors capitalize ${
                  filter === f ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {f === 'all' ? `All (${signals.length})` : f === 'forex' ? `Forex (${signals.filter(s => s.asset_type === 'forex').length})` : `Options (${signals.filter(s => s.asset_type !== 'forex').length})`}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-4">
          {lastScan && <span className="text-xs text-gray-600">Last scan: {lastScan}</span>}
          <button
            onClick={runScan}
            disabled={scanning}
            className="px-4 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {scanning ? 'Scanning...' : 'Scan Markets'}
          </button>
        </div>
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 rounded-lg bg-gray-800 text-xs text-gray-300 border border-gray-700">
          {message}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        {/* Signal List (left panel) */}
        <div className="w-96 border-r border-gray-800 overflow-y-auto flex-shrink-0">
          {filteredSignals.length === 0 ? (
            <div className="p-8 text-center">
              <div className="text-gray-600 text-lg mb-2">No signals</div>
              <div className="text-gray-700 text-sm mb-4">Click "Scan Markets" to analyze 16 instruments</div>
              <button onClick={runScan} className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm">
                Scan Markets
              </button>
            </div>
          ) : (
            filteredSignals.map((s, i) => (
              <SignalRow
                key={s.id || i}
                signal={s}
                isSelected={selectedSignal?.id === s.id}
                onSelect={setSelectedSignal}
              />
            ))
          )}
        </div>

        {/* Main Content (center) */}
        <div className="flex-1 overflow-y-auto p-4">
          {selectedSignal ? (
            <SignalDetail
              signal={selectedSignal}
              onPaperTrade={paperTrade}
              onClose={() => setSelectedSignal(null)}
            />
          ) : (
            /* Positions Dashboard when no signal selected */
            <div>
              {livePositions.length > 0 ? (
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-bold">Open Positions</h2>
                    <div className={`text-lg font-bold font-mono ${totalUnrealized >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      Unrealized: {totalUnrealized >= 0 ? '+' : ''}${totalUnrealized.toFixed(2)}
                    </div>
                  </div>
                  <div className="space-y-3">
                    {livePositions.map((pos: any) => {
                      const isBuy = pos.direction === 'BUY'
                      const pnlColor = pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                      const progressColor = pos.progress_pct >= 0
                        ? (pos.progress_pct >= 80 ? 'bg-green-500' : 'bg-green-500/60')
                        : (pos.progress_pct <= -60 ? 'bg-red-500' : 'bg-red-500/60')

                      return (
                        <div key={pos.id} className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
                          {/* Position Header */}
                          <div className={`px-4 py-3 flex items-center justify-between ${isBuy ? 'border-l-4 border-l-green-500' : 'border-l-4 border-l-red-500'}`}>
                            <div className="flex items-center gap-3">
                              <span className={`text-lg font-black ${isBuy ? 'text-green-400' : 'text-red-400'}`}>
                                {isBuy ? '\u25B2' : '\u25BC'} {pos.direction}
                              </span>
                              <TVLink href={getTVChartUrl(pos.symbol, 'D')}
                                className="text-lg font-bold font-mono text-white hover:text-blue-400 transition-colors">
                                {pos.symbol}
                              </TVLink>
                              <span className={`text-xs px-1.5 py-0.5 rounded ${pos.account === 'forex' ? 'bg-blue-400/15 text-blue-400' : 'bg-purple-400/15 text-purple-400'}`}>
                                {pos.account === 'forex' ? 'FOREX' : 'OPTIONS'}
                              </span>
                              <span className={`text-xs font-bold ${gradeColors[pos.grade] || 'text-gray-400'}`}>{pos.grade}</span>
                            </div>
                            <div className="flex items-center gap-4">
                              <div className="text-right">
                                <div className={`text-xl font-black font-mono ${pnlColor}`}>
                                  {pos.unrealized_pnl >= 0 ? '+' : ''}${pos.unrealized_pnl.toFixed(2)}
                                </div>
                                <div className={`text-xs font-mono ${pnlColor}`}>
                                  {pos.r_multiple >= 0 ? '+' : ''}{pos.r_multiple.toFixed(2)}R
                                </div>
                              </div>
                              <button
                                onClick={() => closeTrade(pos.id, pos.symbol)}
                                disabled={closingId === pos.id}
                                className="px-4 py-2 rounded-lg bg-gray-700 text-white text-sm font-medium hover:bg-gray-600 disabled:opacity-50 transition-colors"
                              >
                                {closingId === pos.id ? 'Closing...' : 'Close'}
                              </button>
                            </div>
                          </div>

                          {/* Price & Levels */}
                          <div className="px-4 py-3 grid grid-cols-5 gap-4 text-sm">
                            <div>
                              <div className="text-[10px] text-gray-600 uppercase">Entry</div>
                              <div className="font-mono text-gray-300">{pos.entry_price}</div>
                            </div>
                            <div>
                              <div className="text-[10px] text-blue-400 uppercase">Current</div>
                              <div className="font-mono text-white font-bold">{pos.current_price ?? '...'}</div>
                            </div>
                            <div>
                              <div className="text-[10px] text-red-400 uppercase">Stop</div>
                              <div className="font-mono text-red-300">{pos.stop_loss}</div>
                            </div>
                            <div>
                              <div className="text-[10px] text-green-400 uppercase">Target</div>
                              <div className="font-mono text-green-300">{pos.target_1}</div>
                            </div>
                            <div>
                              <div className="text-[10px] text-amber-400 uppercase">R/R</div>
                              <div className="font-mono text-amber-300">{pos.risk_reward}:1</div>
                            </div>
                          </div>

                          {/* Progress Bar: Stop ←———→ Target */}
                          <div className="px-4 pb-3">
                            <div className="flex items-center gap-2 text-[10px] text-gray-600 mb-1">
                              <span className="text-red-400">STOP</span>
                              <div className="flex-1" />
                              <span>ENTRY</span>
                              <div className="flex-1" />
                              <span className="text-green-400">TARGET</span>
                            </div>
                            <div className="h-2 bg-gray-700 rounded-full overflow-hidden relative">
                              {/* Entry marker at center */}
                              <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gray-500" />
                              {/* Progress fill */}
                              {pos.progress_pct >= 0 ? (
                                <div
                                  className={`absolute top-0 bottom-0 left-1/2 rounded-r-full ${progressColor}`}
                                  style={{ width: `${Math.min(Math.abs(pos.progress_pct), 100) / 2}%` }}
                                />
                              ) : (
                                <div
                                  className={`absolute top-0 bottom-0 rounded-l-full ${progressColor}`}
                                  style={{
                                    width: `${Math.min(Math.abs(pos.progress_pct), 100) / 2}%`,
                                    right: '50%',
                                  }}
                                />
                              )}
                            </div>
                            <div className="flex justify-between text-[10px] mt-1">
                              <span className={pos.hit_stop ? 'text-red-400 font-bold' : 'text-gray-700'}>
                                {pos.hit_stop ? 'HIT STOP' : ''}
                              </span>
                              <span className="text-gray-600 font-mono">{pos.progress_pct > 0 ? '+' : ''}{pos.progress_pct}%</span>
                              <span className={pos.hit_target ? 'text-green-400 font-bold' : 'text-gray-700'}>
                                {pos.hit_target ? 'HIT TARGET!' : ''}
                              </span>
                            </div>
                          </div>

                          {/* Warnings */}
                          {(pos.hit_stop || pos.hit_target) && (
                            <div className={`px-4 py-2 text-xs font-medium ${pos.hit_target ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                              {pos.hit_target
                                ? `\u2705 Target reached! Close now to lock in $${pos.unrealized_pnl.toFixed(2)} profit.`
                                : `\u26A0\uFE0F Stop level hit! Close to limit loss to $${Math.abs(pos.unrealized_pnl).toFixed(2)}.`
                              }
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="text-gray-700 text-lg mb-1">Select a signal or view positions</div>
                    <div className="text-gray-800 text-sm">Click any signal on the left, or paper trade to see positions here</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Risk Sidebar (right) */}
        <div className="w-64 bg-gray-900/50 border-l border-gray-800 p-4 overflow-y-auto flex-shrink-0">
          <h2 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-4">Accounts</h2>

          {risk ? (
            <>
              <div className="mb-5">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-blue-400 text-xs font-medium">Forex</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${risk.forex.trading_paused ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
                    {risk.forex.trading_paused ? 'PAUSED' : 'ACTIVE'}
                  </span>
                </div>
                <div className="text-xl font-bold font-mono">${risk.forex.account_balance.toFixed(0)}</div>
                <div className={`text-xs font-mono ${risk.forex.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {risk.forex.daily_pnl >= 0 ? '+' : ''}${risk.forex.daily_pnl.toFixed(2)} today
                </div>
                <RiskGauge label="Daily Risk" value={risk.forex.daily_risk_used_pct} max={100} />
                <RiskGauge label="Positions" value={risk.forex.open_positions} max={risk.forex.max_positions} unit="" />
              </div>

              <div className="mb-5">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-purple-400 text-xs font-medium">Options</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${risk.options.trading_paused ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
                    {risk.options.trading_paused ? 'PAUSED' : 'ACTIVE'}
                  </span>
                </div>
                <div className="text-xl font-bold font-mono">${risk.options.account_balance.toFixed(0)}</div>
                <div className={`text-xs font-mono ${risk.options.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {risk.options.daily_pnl >= 0 ? '+' : ''}${risk.options.daily_pnl.toFixed(2)} today
                </div>
                <RiskGauge label="Daily Risk" value={risk.options.daily_risk_used_pct} max={100} />
                <RiskGauge label="Positions" value={risk.options.open_positions} max={risk.options.max_positions} unit="" />
              </div>

              <div className="border-t border-gray-800 pt-4">
                <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Total</div>
                <div className="text-2xl font-bold font-mono">${risk.portfolio.total_balance.toFixed(0)}</div>
                <div className={`text-sm font-mono ${risk.portfolio.total_daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {risk.portfolio.total_daily_pnl >= 0 ? '+' : ''}${risk.portfolio.total_daily_pnl.toFixed(2)}
                </div>
              </div>
              {/* Paper Positions */}
              {livePositions.length > 0 && (
                <div className="border-t border-gray-800 pt-4 mt-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-[10px] text-gray-600 uppercase tracking-wider">
                      Positions ({livePositions.length})
                    </div>
                    <div className={`text-xs font-mono font-bold ${totalUnrealized >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {totalUnrealized >= 0 ? '+' : ''}${totalUnrealized.toFixed(2)}
                    </div>
                  </div>
                  <div className="space-y-2">
                    {livePositions.map((t: any) => (
                      <div
                        key={t.id}
                        onClick={() => { setSelectedSignal(null) }}
                        className={`rounded-lg p-2 text-xs border cursor-pointer hover:border-opacity-60 transition-colors ${
                          t.direction === 'BUY' ? 'bg-green-500/5 border-green-500/20' : 'bg-red-500/5 border-red-500/20'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className={`font-bold ${t.direction === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                            {t.direction === 'BUY' ? '\u25B2' : '\u25BC'} {t.symbol}
                          </span>
                          <span className={`font-mono font-bold ${t.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {t.unrealized_pnl >= 0 ? '+' : ''}${t.unrealized_pnl.toFixed(2)}
                          </span>
                        </div>
                        <div className="flex justify-between mt-1">
                          <span className="text-gray-500 font-mono">@ {t.entry_price}</span>
                          <span className="text-blue-400 font-mono">{t.current_price ?? '...'}</span>
                        </div>
                        {/* Mini progress bar */}
                        <div className="h-1 bg-gray-700 rounded-full overflow-hidden mt-1.5 relative">
                          <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gray-500" />
                          {t.progress_pct >= 0 ? (
                            <div className="absolute top-0 bottom-0 left-1/2 rounded-r-full bg-green-500"
                              style={{ width: `${Math.min(Math.abs(t.progress_pct), 100) / 2}%` }} />
                          ) : (
                            <div className="absolute top-0 bottom-0 rounded-l-full bg-red-500"
                              style={{ width: `${Math.min(Math.abs(t.progress_pct), 100) / 2}%`, right: '50%' }} />
                          )}
                        </div>
                        <div className="flex justify-between mt-1">
                          <span className="text-gray-600 font-mono">{t.r_multiple >= 0 ? '+' : ''}{t.r_multiple.toFixed(1)}R</span>
                          <button
                            onClick={(e) => { e.stopPropagation(); closeTrade(t.id, t.symbol) }}
                            disabled={closingId === t.id}
                            className="text-gray-500 hover:text-white text-[10px] px-1.5 py-0.5 rounded bg-gray-800 hover:bg-gray-700 transition-colors"
                          >
                            {closingId === t.id ? '...' : 'Close'}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Paper Stats */}
              {paperStats && (paperStats.forex?.total_trades > 0 || paperStats.options?.total_trades > 0) && (
                <div className="border-t border-gray-800 pt-4 mt-4">
                  <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-2">Paper Performance</div>
                  {['forex', 'options'].map(key => {
                    const s = paperStats[key]
                    if (!s || s.total_trades === 0) return null
                    return (
                      <div key={key} className="mb-2">
                        <div className="text-xs text-gray-500 capitalize">{key}</div>
                        <div className="flex justify-between text-xs font-mono">
                          <span>{s.total_trades} trades</span>
                          <span className={s.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}>
                            {s.win_rate || 0}% WR
                          </span>
                          <span className={s.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                            ${s.total_pnl?.toFixed(2) || '0.00'}
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
              {/* Market Context — News & Sentiment */}
              {marketCtx && (
                <div className="border-t border-gray-800 pt-4 mt-4">
                  {/* Fear & Greed */}
                  {marketCtx.fear_greed?.score != null && (
                    <div className="mb-3">
                      <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Fear & Greed</div>
                      <div className="flex items-center gap-2">
                        <div className={`text-lg font-bold font-mono ${
                          marketCtx.fear_greed.score <= 25 ? 'text-red-400' :
                          marketCtx.fear_greed.score <= 45 ? 'text-orange-400' :
                          marketCtx.fear_greed.score <= 55 ? 'text-gray-300' :
                          marketCtx.fear_greed.score <= 75 ? 'text-green-400' : 'text-green-300'
                        }`}>
                          {marketCtx.fear_greed.score}
                        </div>
                        <div className="text-xs text-gray-500">{marketCtx.fear_greed.classification}</div>
                      </div>
                    </div>
                  )}

                  {/* Sentiment */}
                  {marketCtx.sentiment?.composite_score != null && (
                    <div className="mb-3">
                      <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Sentiment</div>
                      <div className="flex items-center gap-2">
                        <div className="text-sm font-mono text-gray-300">{marketCtx.sentiment.composite_score}/100</div>
                        <div className="text-xs text-gray-500">{marketCtx.sentiment.classification}</div>
                      </div>
                    </div>
                  )}

                  {/* Economic Events */}
                  {marketCtx.economic_events?.length > 0 && (
                    <div className="mb-3">
                      <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">
                        Events ({marketCtx.economic_events.length})
                      </div>
                      <div className="space-y-1">
                        {marketCtx.economic_events.slice(0, 4).map((e: any, i: number) => (
                          <div key={i} className="text-[10px] flex items-start gap-1">
                            <span className={`px-1 rounded font-bold ${
                              e.impact === 'high' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/15 text-yellow-500'
                            }`}>
                              {e.impact === 'high' ? '!' : '\u25CB'}
                            </span>
                            <span className="text-gray-400 leading-tight">{e.event}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* News Headlines */}
                  {marketCtx.news?.length > 0 && (
                    <div>
                      <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">News</div>
                      <div className="space-y-1.5">
                        {marketCtx.news.slice(0, 5).map((n: any, i: number) => (
                          <div key={i} className="text-[10px] text-gray-500 leading-tight">
                            <span className="text-gray-400">{n.headline?.slice(0, 80) || n.title?.slice(0, 80)}</span>
                            {n.source && <span className="text-gray-700 ml-1">— {n.source}</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="text-gray-700 text-xs">Loading...</div>
          )}
        </div>
      </div>
    </div>
  )
}
