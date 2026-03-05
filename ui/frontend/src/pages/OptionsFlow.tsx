import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Search, TrendingUp, TrendingDown, Activity, ExternalLink,
  GraduationCap, Shield, Target, Gauge, BarChart3, Clock, Newspaper, Zap
} from 'lucide-react'
import api from '../api/client'
import { useApi } from '../hooks/useApi'
import LoadingSpinner from '../components/common/LoadingSpinner'
import InfoTooltip from '../components/common/InfoTooltip'
import LLMAnalysisPanel from '../components/common/LLMAnalysisPanel'
import type {
  OptionsFlowEnhanced,
  OptionsEligibleSymbol,
  ExpiryDistribution,
  StrikeHeatmapEntry,
  DailyFlowBreakdown,
  NewsHeadline,
} from '../api/options-types'

function fmtPremium(val: number): string {
  const abs = Math.abs(val)
  if (abs >= 1e9) return `$${(val / 1e9).toFixed(1)}B`
  if (abs >= 1e6) return `$${(val / 1e6).toFixed(1)}M`
  if (abs >= 1e3) return `$${(val / 1e3).toFixed(1)}K`
  return `$${val.toFixed(0)}`
}

const convictionGradients: Record<string, string> = {
  'Extreme Bull': 'from-green-600 to-green-500',
  'Strong Bull': 'from-green-500 to-emerald-400',
  'Bull': 'from-emerald-500 to-teal-400',
  'Neutral': 'from-gray-600 to-gray-500',
  'Bear': 'from-orange-500 to-red-400',
  'Strong Bear': 'from-red-500 to-red-400',
  'Extreme Bear': 'from-red-700 to-red-500',
}

const convictionBadges: Record<string, string> = {
  'Extreme Bull': 'bg-green-500 text-white',
  'Strong Bull': 'bg-green-400 text-white',
  'Bull': 'bg-green-100 text-green-700',
  'Neutral': 'bg-gray-100 text-gray-700',
  'Bear': 'bg-red-100 text-red-700',
  'Strong Bear': 'bg-red-400 text-white',
  'Extreme Bear': 'bg-red-500 text-white',
}

const sentimentColors: Record<string, string> = {
  'Bullish': 'bg-green-100 text-green-700',
  'Neutral': 'bg-gray-100 text-gray-600',
  'Bearish': 'bg-red-100 text-red-700',
}

const arcStatusColors: Record<string, string> = {
  'Building': 'bg-green-100 text-green-700',
  'Steady': 'bg-blue-100 text-blue-700',
  'Fading': 'bg-orange-100 text-orange-700',
}

export default function OptionsFlow() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialSymbol = searchParams.get('symbol') || ''

  const { data: symbols } = useApi<OptionsEligibleSymbol[]>('/options/symbols')
  const [selectedSymbol, setSelectedSymbol] = useState(initialSymbol)
  const [searchInput, setSearchInput] = useState(initialSymbol)
  const [flow, setFlow] = useState<OptionsFlowEnhanced | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [beginnerMode, setBeginnerMode] = useState(() => {
    return localStorage.getItem('options-beginner-mode') === 'true'
  })

  const toggleBeginner = () => {
    const next = !beginnerMode
    setBeginnerMode(next)
    localStorage.setItem('options-beginner-mode', String(next))
  }

  const fetchFlow = async (sym: string) => {
    if (!sym) return
    setLoading(true)
    setError(null)
    setFlow(null)
    try {
      const res = await api.get<OptionsFlowEnhanced>(`/options/flow/${sym}/enhanced`)
      setFlow(res.data)
      setSelectedSymbol(sym)
      setSearchParams({ symbol: sym })
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch options flow')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (initialSymbol) fetchFlow(initialSymbol)
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const sym = searchInput.trim().toUpperCase()
    if (sym) fetchFlow(sym)
  }

  const sa = flow?.section_analyses

  return (
    <div className="space-y-5">
      {/* Panel 1: Symbol Selector (sticky) */}
      <div className="sticky top-0 z-30 bg-apple-gray-50/95 backdrop-blur-sm pb-3 -mx-1 px-1">
        <div className="bg-white rounded-2xl border border-apple-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-xl font-bold text-apple-gray-800">Options Flow Intelligence</h2>
              <p className="text-sm text-apple-gray-500 mt-0.5">Premium analysis, conviction scoring, and AI insights</p>
            </div>
            <button
              onClick={toggleBeginner}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                beginnerMode
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'bg-apple-gray-50 text-apple-gray-500 hover:bg-apple-gray-100'
              }`}
            >
              <GraduationCap size={14} />
              {beginnerMode ? 'Beginner Mode ON' : 'Beginner Mode'}
            </button>
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-apple-gray-400" size={18} />
              <input
                type="text"
                placeholder="Enter ticker (e.g. NVDA, AAPL, TSLA)"
                value={searchInput}
                onChange={e => setSearchInput(e.target.value.toUpperCase())}
                list="symbol-options"
                className="w-full pl-10 pr-4 py-3 bg-apple-gray-50 rounded-xl text-sm border border-apple-gray-200 focus:outline-none focus:ring-2 focus:ring-apple-blue/30"
              />
              <datalist id="symbol-options">
                {symbols?.map(s => (
                  <option key={s.symbol} value={s.symbol}>{s.name}</option>
                ))}
              </datalist>
            </div>
            <button
              type="submit"
              className="px-6 py-3 bg-apple-blue text-white text-sm font-semibold rounded-xl hover:bg-blue-600 transition-colors"
            >
              Analyze
            </button>
          </form>

          {symbols && symbols.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {symbols.slice(0, 15).map(s => (
                <button
                  key={s.symbol}
                  onClick={() => { setSearchInput(s.symbol); fetchFlow(s.symbol) }}
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                    selectedSymbol === s.symbol
                      ? 'bg-apple-blue text-white'
                      : 'bg-apple-gray-50 text-apple-gray-600 hover:bg-apple-gray-100'
                  }`}
                >
                  {s.symbol}
                </button>
              ))}
            </div>
          )}

          {/* Stock price when loaded */}
          {flow && !loading && (
            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-apple-gray-100">
              <span className="text-lg font-bold text-apple-gray-800">{flow.symbol}</span>
              <span className="text-lg font-semibold text-apple-gray-600">${flow.stock_price.toFixed(2)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Loading / Error */}
      {loading && (
        <div className="text-center py-12">
          <LoadingSpinner size="lg" className="mb-3" />
          <p className="text-sm text-apple-gray-500">Analyzing options flow for {searchInput}...</p>
          <p className="text-xs text-apple-gray-400 mt-1">This may take a moment</p>
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-5 text-sm text-red-700">{error}</div>
      )}

      {/* Results */}
      {flow && !loading && (
        <div className="space-y-5">
          {/* Panel 2: Verdict Banner */}
          <VerdictBanner flow={flow} analysis={sa?.flow_summary ?? null} beginnerMode={beginnerMode} />

          {/* Panel 3: Premium Flow */}
          <PremiumFlow flow={flow} analysis={sa?.premium_analysis ?? null} beginnerMode={beginnerMode} />

          {/* Panel 4: Greeks & Positioning */}
          <GreeksPanel flow={flow} analysis={sa?.greeks_analysis ?? null} beginnerMode={beginnerMode} />

          {/* Panel 5: Strike Heatmap */}
          <StrikeHeatmap heatmap={flow.strike_heatmap} analysis={sa?.strike_analysis ?? null} beginnerMode={beginnerMode} />

          {/* Panel 6: Expiry Distribution */}
          <ExpiryDistributionPanel distribution={flow.expiry_distribution} analysis={sa?.expiry_analysis ?? null} beginnerMode={beginnerMode} />

          {/* Panel 7: Daily Flow Timeline */}
          <DailyFlowTimeline breakdown={flow.daily_breakdown} arcStatus={flow.arc_status} arcReading={flow.arc_reading} beginnerMode={beginnerMode} />

          {/* Panel 8: News & Correlation */}
          <NewsPanel headlines={flow.news_headlines || []} analysis={sa?.news_correlation ?? null} beginnerMode={beginnerMode} />

          {/* Panel 9: Action Items */}
          <ActionItems analysis={sa?.action_items ?? null} beginnerMode={beginnerMode} />
        </div>
      )}
    </div>
  )
}

/* ── Panel 2: Verdict Banner ──────────────────────────────────── */

function VerdictBanner({ flow, analysis, beginnerMode }: { flow: OptionsFlowEnhanced; analysis: string | null; beginnerMode: boolean }) {
  const gradient = convictionGradients[flow.conviction] || 'from-gray-600 to-gray-500'
  const arcBadge = arcStatusColors[flow.arc_status] || 'bg-gray-100 text-gray-600'

  return (
    <div className={`bg-gradient-to-r ${gradient} rounded-2xl p-6 text-white shadow-lg`}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="text-4xl font-black">{flow.conviction_score}</span>
            <span className="text-lg font-medium text-white/70">/100</span>
          </div>
          <span className="text-lg font-bold">{flow.conviction}</span>
        </div>
        <div className="flex gap-2">
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${arcBadge}`}>
            Arc: {flow.arc_status}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 text-center bg-white/10 rounded-xl p-4">
        <div>
          <p className="text-xs text-white/60">Total Premium</p>
          <p className="text-xl font-bold">{fmtPremium(flow.total_premium)}</p>
        </div>
        <div>
          <p className="text-xs text-white/60">C/P Ratio</p>
          <p className="text-xl font-bold">{flow.cp_ratio.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-xs text-white/60">Top Call Target</p>
          <p className="text-xl font-bold">
            {flow.top_call_strike ? `$${flow.top_call_strike}` : '-'}
          </p>
        </div>
      </div>

      {/* LLM flow summary inline */}
      {analysis && (
        <p className="mt-4 text-sm text-white/90 leading-relaxed">{analysis}</p>
      )}
      {!analysis && beginnerMode && (
        <p className="mt-4 text-sm text-white/60 italic">Enable LLM for a plain-English flow summary</p>
      )}
    </div>
  )
}

/* ── Panel 3: Premium Flow ────────────────────────────────────── */

function PremiumFlow({ flow, analysis, beginnerMode }: { flow: OptionsFlowEnhanced; analysis: string | null; beginnerMode: boolean }) {
  const total = flow.total_call_premium + flow.total_put_premium
  const callPct = total > 0 ? (flow.total_call_premium / total) * 100 : 50
  const putPct = 100 - callPct

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Premium Flow</h3>
        <InfoTooltip
          text="Premium = estimated dollar value of options traded. Higher call premium = bullish bets. Higher put premium = bearish bets or hedging. The C/P ratio shows the balance."
          forceOpen={false}
        />
      </div>

      {/* Large split bar */}
      <div className="flex rounded-full overflow-hidden h-10 mb-4">
        <div
          className="bg-green-400 flex items-center justify-center text-sm font-bold text-white transition-all"
          style={{ width: `${callPct}%` }}
        >
          {callPct >= 15 && `${callPct.toFixed(0)}% Calls`}
        </div>
        <div
          className="bg-red-400 flex items-center justify-center text-sm font-bold text-white transition-all"
          style={{ width: `${putPct}%` }}
        >
          {putPct >= 15 && `${putPct.toFixed(0)}% Puts`}
        </div>
      </div>

      {/* 2x2 stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <BigStatCard label="Call Premium" value={fmtPremium(flow.total_call_premium)} color="text-green-600" icon={<TrendingUp size={18} />} />
        <BigStatCard label="Put Premium" value={fmtPremium(flow.total_put_premium)} color="text-red-600" icon={<TrendingDown size={18} />} />
        <BigStatCard label="C/P Ratio" value={flow.cp_ratio.toFixed(2)} color={flow.cp_ratio >= 1 ? 'text-green-600' : 'text-red-600'} />
        <BigStatCard label="Total Premium" value={fmtPremium(flow.total_premium)} color="text-apple-gray-800" />
      </div>

      <LLMAnalysisPanel analysis={analysis} defaultOpen={beginnerMode} />
    </div>
  )
}

function BigStatCard({ label, value, color, icon }: { label: string; value: string; color: string; icon?: React.ReactNode }) {
  return (
    <div className="bg-apple-gray-50 rounded-xl p-4">
      <div className="flex items-center gap-1.5 mb-1.5">
        {icon && <span className={color}>{icon}</span>}
        <p className="text-xs text-apple-gray-400 font-medium">{label}</p>
      </div>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

/* ── Panel 4: Greeks & Positioning ────────────────────────────── */

function GreeksPanel({ flow, analysis, beginnerMode }: { flow: OptionsFlowEnhanced; analysis: string | null; beginnerMode: boolean }) {
  const g = flow.greeks_summary
  const oi = flow.oi_analysis
  const price = flow.stock_price

  // Calculate positioning for the price line visual
  const levels = [g.put_wall, g.max_pain, price, g.call_wall].filter((v): v is number => v != null)
  const min = Math.min(...levels) * 0.995
  const max = Math.max(...levels) * 1.005
  const range = max - min || 1
  const toPos = (v: number) => ((v - min) / range) * 100

  // Delta interpretation
  const deltaLabel = g.net_delta > 50000 ? 'Strongly Bullish'
    : g.net_delta > 10000 ? 'Bullish'
    : g.net_delta > -10000 ? 'Neutral'
    : g.net_delta > -50000 ? 'Bearish'
    : 'Strongly Bearish'

  const deltaColor = g.net_delta > 10000 ? 'text-green-600'
    : g.net_delta < -10000 ? 'text-red-600'
    : 'text-gray-600'

  // Gamma interpretation
  const gammaLabel = g.total_gamma > 100000 ? 'High (dealers will amplify moves)'
    : g.total_gamma > 10000 ? 'Moderate'
    : 'Low (dealers less impactful)'

  // Put/Call OI ratio interpretation
  const pcrLabel = oi.pcr_oi > 1.2 ? 'Bearish (more puts than calls)'
    : oi.pcr_oi > 0.8 ? 'Neutral balance'
    : 'Bullish (more calls than puts)'

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Shield size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Greeks & Positioning</h3>
        <InfoTooltip
          text="Greeks measure how option prices change. Max Pain = the price where most options expire worthless (a magnet for stock price near expiry). Put Wall = highest put open interest strike (acts as support). Call Wall = highest call OI (acts as resistance). Net Delta = overall directional exposure. Gamma = how fast delta changes (high gamma = bigger dealer hedging moves)."
          forceOpen={false}
        />
      </div>

      {/* Price Line Visual */}
      {g.put_wall != null && g.call_wall != null && g.max_pain != null && (
        <div className="mb-5 px-2">
          <p className="text-xs text-apple-gray-400 mb-2 font-medium">Price Positioning</p>
          <div className="relative h-12 bg-apple-gray-50 rounded-xl">
            {/* Range bar */}
            <div className="absolute top-5 left-0 right-0 h-1 bg-apple-gray-200 rounded-full" />

            {/* Put Wall marker */}
            {g.put_wall != null && (
              <div className="absolute top-0" style={{ left: `${toPos(g.put_wall)}%`, transform: 'translateX(-50%)' }}>
                <div className="flex flex-col items-center">
                  <span className="text-[10px] font-bold text-red-500 whitespace-nowrap">Put Wall</span>
                  <div className="w-0.5 h-3 bg-red-400" />
                  <div className="w-3 h-3 rounded-full bg-red-400 border-2 border-white shadow" />
                  <span className="text-[10px] text-red-500 font-medium mt-0.5">${g.put_wall}</span>
                </div>
              </div>
            )}

            {/* Max Pain marker */}
            {g.max_pain != null && (
              <div className="absolute top-0" style={{ left: `${toPos(g.max_pain)}%`, transform: 'translateX(-50%)' }}>
                <div className="flex flex-col items-center">
                  <span className="text-[10px] font-bold text-amber-600 whitespace-nowrap">Max Pain</span>
                  <div className="w-0.5 h-3 bg-amber-400" />
                  <div className="w-3 h-3 rounded-full bg-amber-400 border-2 border-white shadow" />
                  <span className="text-[10px] text-amber-600 font-medium mt-0.5">${g.max_pain}</span>
                </div>
              </div>
            )}

            {/* Current Price marker */}
            <div className="absolute top-0" style={{ left: `${toPos(price)}%`, transform: 'translateX(-50%)' }}>
              <div className="flex flex-col items-center">
                <span className="text-[10px] font-bold text-apple-blue whitespace-nowrap">Price</span>
                <div className="w-0.5 h-3 bg-apple-blue" />
                <div className="w-3.5 h-3.5 rounded-full bg-apple-blue border-2 border-white shadow" />
                <span className="text-[10px] text-apple-blue font-medium mt-0.5">${price.toFixed(2)}</span>
              </div>
            </div>

            {/* Call Wall marker */}
            {g.call_wall != null && (
              <div className="absolute top-0" style={{ left: `${toPos(g.call_wall)}%`, transform: 'translateX(-50%)' }}>
                <div className="flex flex-col items-center">
                  <span className="text-[10px] font-bold text-green-500 whitespace-nowrap">Call Wall</span>
                  <div className="w-0.5 h-3 bg-green-400" />
                  <div className="w-3 h-3 rounded-full bg-green-400 border-2 border-white shadow" />
                  <span className="text-[10px] text-green-500 font-medium mt-0.5">${g.call_wall}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Detailed Greek Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <GreekDetailCard
          label="Max Pain"
          value={g.max_pain != null ? `$${g.max_pain}` : '-'}
          explanation="The price where most options expire worthless. Stock prices tend to gravitate toward max pain near expiration."
          icon={<Target size={16} />}
          beginnerMode={beginnerMode}
        />
        <GreekDetailCard
          label="Put Wall (Support)"
          value={g.put_wall != null ? `$${g.put_wall}` : '-'}
          explanation="Strike with the most put open interest. Heavy put OI acts as a support floor — dealers hedging puts buy stock as it drops toward this level."
          color="text-red-600"
          icon={<Shield size={16} />}
          beginnerMode={beginnerMode}
        />
        <GreekDetailCard
          label="Call Wall (Resistance)"
          value={g.call_wall != null ? `$${g.call_wall}` : '-'}
          explanation="Strike with the most call open interest. Heavy call OI acts as a resistance ceiling — dealers hedging calls sell stock as it rises toward this level."
          color="text-green-600"
          icon={<Shield size={16} />}
          beginnerMode={beginnerMode}
        />
        <GreekDetailCard
          label="Net Delta"
          value={g.net_delta != null ? `${g.net_delta > 0 ? '+' : ''}${g.net_delta.toLocaleString()}` : '-'}
          subtitle={deltaLabel}
          explanation="Sum of all delta exposure across all options. Positive = market makers are net long (bullish positioning). Negative = net short (bearish). This shows the aggregate directional bet."
          color={deltaColor}
          icon={<Gauge size={16} />}
          beginnerMode={beginnerMode}
        />
        <GreekDetailCard
          label="Total Gamma"
          value={g.total_gamma != null ? g.total_gamma.toLocaleString() : '-'}
          subtitle={gammaLabel}
          explanation="Gamma measures how much delta changes when the stock moves $1. High total gamma means market makers will hedge aggressively, amplifying price moves. This creates faster breakouts or reversals."
          icon={<Activity size={16} />}
          beginnerMode={beginnerMode}
        />
        <GreekDetailCard
          label="Put/Call OI Ratio"
          value={oi.pcr_oi.toFixed(2)}
          subtitle={pcrLabel}
          explanation="Ratio of total put open interest to call open interest. Above 1.0 = more puts (bearish or hedging). Below 0.7 = more calls (bullish). Extreme readings can signal sentiment turning points."
          icon={<BarChart3 size={16} />}
          beginnerMode={beginnerMode}
        />
      </div>

      {/* OI Totals */}
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="bg-green-50 rounded-xl p-3 text-center">
          <p className="text-xs text-green-600 font-medium">Total Call OI</p>
          <p className="text-xl font-bold text-green-700">{oi.total_call_oi.toLocaleString()}</p>
          {beginnerMode && <p className="text-[10px] text-green-500 mt-1">Open interest = existing contracts still held</p>}
        </div>
        <div className="bg-red-50 rounded-xl p-3 text-center">
          <p className="text-xs text-red-600 font-medium">Total Put OI</p>
          <p className="text-xl font-bold text-red-700">{oi.total_put_oi.toLocaleString()}</p>
          {beginnerMode && <p className="text-[10px] text-red-500 mt-1">More put OI = more hedging or bearish bets</p>}
        </div>
      </div>

      <LLMAnalysisPanel analysis={analysis} defaultOpen={beginnerMode} />
    </div>
  )
}

function GreekDetailCard({ label, value, subtitle, explanation, color, icon, beginnerMode }: {
  label: string; value: string; subtitle?: string; explanation: string; color?: string; icon?: React.ReactNode; beginnerMode: boolean
}) {
  return (
    <div className="bg-apple-gray-50 rounded-xl p-4">
      <div className="flex items-center gap-1.5 mb-1">
        {icon && <span className={color || 'text-apple-gray-500'}>{icon}</span>}
        <p className="text-xs text-apple-gray-500 font-medium">{label}</p>
      </div>
      <p className={`text-xl font-bold ${color || 'text-apple-gray-800'}`}>{value}</p>
      {subtitle && <p className={`text-[11px] font-medium mt-0.5 ${color || 'text-apple-gray-500'}`}>{subtitle}</p>}
      {beginnerMode && (
        <p className="text-[10px] text-apple-gray-400 mt-2 leading-relaxed">{explanation}</p>
      )}
    </div>
  )
}

/* ── Panel 5: Strike Heatmap ──────────────────────────────────── */

function StrikeHeatmap({ heatmap, analysis, beginnerMode }: { heatmap: StrikeHeatmapEntry[]; analysis: string | null; beginnerMode: boolean }) {
  if (!heatmap.length) return null

  const maxPrem = Math.max(...heatmap.map(h => Math.max(h.call_premium, h.put_premium)))

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Target size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Strike Heatmap</h3>
        <InfoTooltip
          text="Strikes with the highest premium show where traders are placing their biggest bets. Green bars = call premium (bullish bets). Red bars = put premium (bearish bets or hedging)."
          forceOpen={false}
        />
      </div>
      <div className="space-y-1.5">
        {heatmap.map((h, i) => {
          const callWidth = maxPrem > 0 ? (h.call_premium / maxPrem) * 100 : 0
          const putWidth = maxPrem > 0 ? (h.put_premium / maxPrem) * 100 : 0
          const isTop3 = i < 3
          return (
            <div key={i} className={`flex items-center gap-2 ${isTop3 ? 'bg-amber-50 rounded-lg px-1 py-0.5' : ''}`}>
              <div className="w-20 text-right shrink-0">
                <span className="text-[10px] text-apple-gray-400">{fmtPremium(h.put_premium)}</span>
              </div>
              <div className="flex-1 flex items-center gap-0">
                <div className="flex-1 flex justify-end">
                  <div
                    className="h-6 bg-red-300 rounded-l transition-all"
                    style={{ width: `${putWidth}%` }}
                  />
                </div>
                <div className="w-20 text-center shrink-0">
                  <span className={`text-xs font-bold ${isTop3 ? 'text-amber-700' : 'text-apple-gray-700'}`}>
                    ${h.strike}
                  </span>
                </div>
                <div className="flex-1">
                  <div
                    className="h-6 bg-green-300 rounded-r transition-all"
                    style={{ width: `${callWidth}%` }}
                  />
                </div>
              </div>
              <div className="w-20 shrink-0">
                <span className="text-[10px] text-apple-gray-400">{fmtPremium(h.call_premium)}</span>
              </div>
            </div>
          )
        })}
        <div className="flex justify-between text-[10px] text-apple-gray-400 mt-2 px-20">
          <span>Put Premium</span>
          <span>Call Premium</span>
        </div>
      </div>

      <LLMAnalysisPanel analysis={analysis} defaultOpen={beginnerMode} />
    </div>
  )
}

/* ── Panel 6: Expiry Distribution ─────────────────────────────── */

function ExpiryDistributionPanel({ distribution, analysis, beginnerMode }: { distribution: ExpiryDistribution[]; analysis: string | null; beginnerMode: boolean }) {
  if (!distribution.length) return null

  const maxPrem = Math.max(...distribution.map(d => d.total_premium))

  const expiryColor = (days: number) => {
    if (days < 7) return 'bg-red-400'
    if (days < 30) return 'bg-amber-400'
    return 'bg-blue-400'
  }

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Clock size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Expiry Distribution</h3>
        <InfoTooltip
          text="Near-term expiries (red, <7 days) signal urgent conviction. Medium-term (yellow, 7-30 days) are standard positioning. Far-out dates (blue, 30+ days) suggest longer-term strategic bets."
          forceOpen={false}
        />
      </div>

      {/* Color legend */}
      <div className="flex gap-4 mb-3 text-[10px] text-apple-gray-500">
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-red-400" /> &lt;7 days</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-amber-400" /> 7-30 days</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-blue-400" /> 30+ days</span>
      </div>

      <div className="space-y-2.5">
        {distribution.map((d, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="w-28 shrink-0">
              <p className="text-xs font-semibold text-apple-gray-700">{d.expiry}</p>
              <p className="text-[10px] text-apple-gray-400">
                {d.days_to_expiry}d{d.top_strike ? ` | Top: $${d.top_strike}` : ''}
              </p>
            </div>
            <div className="flex-1 h-6 bg-apple-gray-50 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${expiryColor(d.days_to_expiry)}`}
                style={{ width: `${maxPrem > 0 ? (d.total_premium / maxPrem) * 100 : 0}%` }}
              />
            </div>
            <div className="w-24 text-right shrink-0">
              <p className="text-xs font-semibold text-apple-gray-700">{fmtPremium(d.total_premium)}</p>
              <p className="text-[10px] text-apple-gray-400">{d.pct_of_total.toFixed(0)}% | C/P {d.cp_ratio.toFixed(1)}</p>
            </div>
          </div>
        ))}
      </div>

      <LLMAnalysisPanel analysis={analysis} defaultOpen={beginnerMode} />
    </div>
  )
}

/* ── Panel 7: Daily Flow Timeline ─────────────────────────────── */

function DailyFlowTimeline({ breakdown, arcStatus, arcReading, beginnerMode }: {
  breakdown: DailyFlowBreakdown[]; arcStatus: string; arcReading: string | null; beginnerMode: boolean
}) {
  const arcBadge = arcStatusColors[arcStatus] || 'bg-gray-100 text-gray-600'

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-apple-blue" />
          <h3 className="text-base font-bold text-apple-gray-800">Daily Flow Timeline</h3>
        </div>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${arcBadge}`}>
          Arc: {arcStatus}
        </span>
      </div>

      {breakdown.length < 2 ? (
        <p className="text-xs text-apple-gray-400 text-center py-6">
          Daily history builds automatically. Check back tomorrow for trend data.
        </p>
      ) : (
        <>
          {/* C/P ratio trend line */}
          <div className="flex items-end gap-1 mb-4 h-16 px-2">
            {[...breakdown].reverse().map((d, i) => {
              const maxRatio = Math.max(...breakdown.map(b => b.cp_ratio))
              const height = maxRatio > 0 ? (d.cp_ratio / maxRatio) * 100 : 50
              const barColor = d.cp_ratio >= 1.5 ? 'bg-green-400'
                : d.cp_ratio >= 0.8 ? 'bg-gray-300'
                : 'bg-red-400'
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                  <span className="text-[9px] text-apple-gray-400">{d.cp_ratio.toFixed(1)}</span>
                  <div className={`w-full rounded-t ${barColor}`} style={{ height: `${height}%` }} />
                </div>
              )
            })}
          </div>

          {/* Day cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5">
            {breakdown.map((d, i) => {
              const total = d.total_call_premium + d.total_put_premium
              const callPct = total > 0 ? (d.total_call_premium / total) * 100 : 50
              const badge = sentimentColors[d.sentiment] || 'bg-gray-100 text-gray-600'
              return (
                <div key={i} className="bg-apple-gray-50 rounded-xl p-3.5 text-center">
                  <p className="text-sm font-bold text-apple-gray-700">{d.day}</p>
                  <p className="text-[10px] text-apple-gray-400">{d.date}</p>
                  <div className="flex rounded-full overflow-hidden h-2.5 mt-2 mb-2">
                    <div className="bg-green-400" style={{ width: `${callPct}%` }} />
                    <div className="bg-red-400" style={{ width: `${100 - callPct}%` }} />
                  </div>
                  <p className="text-xs font-semibold text-apple-gray-700">{fmtPremium(d.total_premium)}</p>
                  <p className="text-[10px] text-apple-gray-400">C/P {d.cp_ratio.toFixed(2)}</p>
                  <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full mt-1.5 ${badge}`}>
                    {d.sentiment}
                  </span>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* Arc reading */}
      {arcReading && (
        <div className="mt-4 p-3 bg-indigo-50 rounded-xl">
          <p className="text-xs text-indigo-900/80 leading-relaxed">{arcReading}</p>
        </div>
      )}
    </div>
  )
}

/* ── Panel 8: News & Correlation ──────────────────────────────── */

function NewsPanel({ headlines, analysis, beginnerMode }: { headlines: NewsHeadline[]; analysis: string | null; beginnerMode: boolean }) {
  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Newspaper size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">News & Correlation</h3>
        <InfoTooltip
          text="Options flow often reacts to or anticipates news events. Seeing heavy call buying before positive news may indicate informed positioning."
          forceOpen={false}
        />
      </div>

      {headlines.length > 0 ? (
        <div className="space-y-2.5">
          {headlines.map((h, i) => (
            <a
              key={i}
              href={h.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-apple-gray-50 rounded-xl p-3.5 hover:bg-apple-gray-100 transition-colors group"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-apple-gray-800 group-hover:text-apple-blue transition-colors line-clamp-2">
                    {h.title}
                  </p>
                  {h.description && (
                    <p className="text-xs text-apple-gray-400 mt-1 line-clamp-1">{h.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-1.5">
                    {h.source && <span className="text-[10px] text-apple-gray-400">{h.source}</span>}
                    {h.published_at && (
                      <span className="text-[10px] text-apple-gray-300">
                        {new Date(h.published_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
                {h.url && <ExternalLink size={14} className="text-apple-gray-300 group-hover:text-apple-blue shrink-0 mt-0.5" />}
              </div>
            </a>
          ))}
        </div>
      ) : (
        <p className="text-xs text-apple-gray-400 text-center py-4">
          No recent news found. News requires a NewsAPI key.
        </p>
      )}

      <LLMAnalysisPanel analysis={analysis} defaultOpen={beginnerMode} />
    </div>
  )
}

/* ── Panel 9: Action Items ────────────────────────────────────── */

function ActionItems({ analysis, beginnerMode }: { analysis: string | null; beginnerMode: boolean }) {
  // Parse numbered items from analysis text
  const items = analysis
    ? analysis.split(/\n/).filter(line => /^\d+[\.\)]/.test(line.trim()))
    : []

  const getItemSentiment = (text: string): 'bullish' | 'bearish' | 'neutral' => {
    const lower = text.toLowerCase()
    if (lower.includes('bullish') || lower.includes('buy') || lower.includes('call') || lower.includes('upside')) return 'bullish'
    if (lower.includes('bearish') || lower.includes('sell') || lower.includes('put') || lower.includes('downside')) return 'bearish'
    return 'neutral'
  }

  const sentimentStyle: Record<string, string> = {
    bullish: 'border-l-green-400 bg-green-50',
    bearish: 'border-l-red-400 bg-red-50',
    neutral: 'border-l-amber-400 bg-amber-50',
  }

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Zap size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Action Items</h3>
        <InfoTooltip
          text="AI-generated suggestions based on the current options data. These are observations, not financial advice. Always do your own research before trading."
          forceOpen={false}
        />
      </div>

      {items.length > 0 ? (
        <div className="space-y-2.5">
          {items.map((item, i) => {
            const sentiment = getItemSentiment(item)
            return (
              <div
                key={i}
                className={`border-l-4 rounded-r-xl p-3.5 ${sentimentStyle[sentiment]}`}
              >
                <p className="text-sm text-apple-gray-700 leading-relaxed">{item.replace(/^\d+[\.\)]\s*/, '')}</p>
              </div>
            )
          })}
        </div>
      ) : analysis ? (
        <div className="bg-apple-gray-50 rounded-xl p-4">
          <p className="text-sm text-apple-gray-700 leading-relaxed">{analysis}</p>
        </div>
      ) : (
        <p className="text-xs text-apple-gray-400 text-center py-4">
          Enable LLM for AI-generated action items
        </p>
      )}

      {beginnerMode && (
        <p className="text-[10px] text-apple-gray-400 mt-3 text-center">
          These are AI-generated observations based on options data. Not financial advice.
        </p>
      )}
    </div>
  )
}
