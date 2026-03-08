import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Search, TrendingUp, TrendingDown, Activity, ExternalLink,
  GraduationCap, Shield, Target, Gauge, BarChart3, Clock, Newspaper, Zap,
  Lock, RefreshCw, Eye, Users, Layers, ChevronDown
} from 'lucide-react'
import api from '../api/client'
import { useApi } from '../hooks/useApi'
import LoadingSpinner from '../components/common/LoadingSpinner'
import InfoTooltip from '../components/common/InfoTooltip'
import LLMAnalysisPanel from '../components/common/LLMAnalysisPanel'
import TimeSeriesChart from '../components/charts/TimeSeriesChart'
import type {
  OptionsFlowV2,
  OptionsFlowEnhanced,
  OptionsEligibleSymbol,
  ExpiryDistribution,
  StrikeHeatmapEntry,
  DailyFlowBreakdown,
  NewsHeadline,
  FlowAlert,
  ProviderStatus,
  ConvictionFactor,
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
  'Strong Bullish': 'from-green-500 to-emerald-400',
  'Bull': 'from-emerald-500 to-teal-400',
  'Bullish': 'from-emerald-500 to-teal-400',
  'Neutral': 'from-gray-600 to-gray-500',
  'Bear': 'from-orange-500 to-red-400',
  'Bearish': 'from-orange-500 to-red-400',
  'Strong Bear': 'from-red-500 to-red-400',
  'Strong Bearish': 'from-red-500 to-red-400',
  'Extreme Bear': 'from-red-700 to-red-500',
}

const convictionBadges: Record<string, string> = {
  'Extreme Bull': 'bg-green-500 text-white',
  'Strong Bull': 'bg-green-400 text-white',
  'Strong Bullish': 'bg-green-400 text-white',
  'Bull': 'bg-green-100 text-green-700',
  'Bullish': 'bg-green-100 text-green-700',
  'Neutral': 'bg-gray-100 text-gray-700',
  'Bear': 'bg-red-100 text-red-700',
  'Bearish': 'bg-red-100 text-red-700',
  'Strong Bear': 'bg-red-400 text-white',
  'Strong Bearish': 'bg-red-400 text-white',
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

type TabId = 'overview' | 'smart_money' | 'volatility' | 'analysis' | 'ai_insights'

interface TabDef {
  id: TabId
  label: string
  icon: React.ReactNode
  requiresProvider?: keyof ProviderStatus
}

const TABS: TabDef[] = [
  { id: 'overview', label: 'Overview', icon: <Eye size={15} /> },
  { id: 'smart_money', label: 'Smart Money', icon: <Users size={15} />, requiresProvider: 'unusual_whales' },
  { id: 'volatility', label: 'Volatility', icon: <Activity size={15} />, requiresProvider: 'alpha_vantage' },
  { id: 'analysis', label: 'Analysis', icon: <Layers size={15} /> },
  { id: 'ai_insights', label: 'AI Insights', icon: <Zap size={15} /> },
]

const REFRESH_OPTIONS = [
  { label: 'Off', ms: 0 },
  { label: '30s', ms: 30000 },
  { label: '1m', ms: 60000 },
  { label: '5m', ms: 300000 },
]

export default function OptionsFlow() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialSymbol = searchParams.get('symbol') || ''

  const { data: symbols } = useApi<OptionsEligibleSymbol[]>('/options/symbols')
  const { data: providers } = useApi<ProviderStatus>('/options/providers')
  const [selectedSymbol, setSelectedSymbol] = useState(initialSymbol)
  const [searchInput, setSearchInput] = useState(initialSymbol)
  const [flow, setFlow] = useState<OptionsFlowV2 | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [refreshInterval, setRefreshInterval] = useState(0)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [beginnerMode, setBeginnerMode] = useState(() => {
    return localStorage.getItem('options-beginner-mode') === 'true'
  })

  const refreshRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const toggleBeginner = () => {
    const next = !beginnerMode
    setBeginnerMode(next)
    localStorage.setItem('options-beginner-mode', String(next))
  }

  const fetchFlow = useCallback(async (sym: string, silent = false) => {
    if (!sym) return
    if (!silent) {
      setLoading(true)
      setError(null)
      setFlow(null)
    }
    try {
      // Try V2 endpoint first, fallback to enhanced
      const res = await api.get<OptionsFlowV2>(`/options/flow/${sym}/v2`)
      setFlow(res.data)
      setSelectedSymbol(sym)
      setSearchParams({ symbol: sym })
      setLastUpdated(new Date())
    } catch {
      try {
        const res = await api.get<OptionsFlowEnhanced>(`/options/flow/${sym}/enhanced`)
        // Map enhanced to V2 shape with null V3 fields
        setFlow({
          ...res.data,
          flow_alerts: null,
          dark_pool: null,
          institutional: null,
          flow_intervals: null,
          historical_iv: null,
          unusual_activity: { available: false, sweep_count: 0, block_count: 0, golden_sweep_count: 0, total_sweep_premium: 0, dominant_side: 'neutral', largest_sweep: null, volume_oi_flags: [] },
          smart_money: { available: false, smart_money_pct: 0, retail_pct: 0, smart_money_sentiment: 'neutral', retail_sentiment: 'neutral', divergence_score: 0 },
          conviction_v2: { score: res.data.conviction_score, label: res.data.conviction, confidence: 'low', factors: [], available_factors: 0, total_factors: 0 },
          iv_analysis: null,
          advanced_greeks: null,
          dp_correlation: null,
          flow_momentum: { cp_momentum: 'stable', intraday_trend: null },
          provider_status: { yfinance: true, unusual_whales: false, alpha_vantage: false },
        } as OptionsFlowV2)
        setSelectedSymbol(sym)
        setSearchParams({ symbol: sym })
        setLastUpdated(new Date())
      } catch (err: any) {
        if (!silent) setError(err.response?.data?.detail || err.message || 'Failed to fetch options flow')
      }
    } finally {
      if (!silent) setLoading(false)
    }
  }, [setSearchParams])

  // Auto-refresh
  useEffect(() => {
    if (refreshRef.current) clearInterval(refreshRef.current)
    if (refreshInterval > 0 && selectedSymbol) {
      refreshRef.current = setInterval(() => fetchFlow(selectedSymbol, true), refreshInterval)
    }
    return () => { if (refreshRef.current) clearInterval(refreshRef.current) }
  }, [refreshInterval, selectedSymbol, fetchFlow])

  useEffect(() => {
    if (initialSymbol) fetchFlow(initialSymbol)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const sym = searchInput.trim().toUpperCase()
    if (sym) fetchFlow(sym)
  }

  const isTabLocked = (tab: TabDef): boolean => {
    if (!tab.requiresProvider) return false
    if (!providers) return false
    return !providers[tab.requiresProvider]
  }

  const sa = flow?.section_analyses
  const ps = flow?.provider_status || providers

  return (
    <div className="space-y-5">
      {/* Symbol Selector (sticky) */}
      <div className="sticky top-0 z-30 bg-apple-gray-50/95 backdrop-blur-sm pb-3 -mx-1 px-1">
        <div className="bg-white rounded-2xl border border-apple-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-xl font-bold text-apple-gray-800">Options Flow Intelligence</h2>
              <p className="text-sm text-apple-gray-500 mt-0.5">
                Premium analysis, conviction scoring, and AI insights
                {ps && (ps.unusual_whales || ps.alpha_vantage) && (
                  <span className="ml-2">
                    {ps.unusual_whales && <span className="inline-flex items-center gap-0.5 text-[10px] bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded-full font-medium ml-1">UW</span>}
                    {ps.alpha_vantage && <span className="inline-flex items-center gap-0.5 text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full font-medium ml-1">AV</span>}
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {/* Auto-refresh selector */}
              <div className="flex items-center gap-1 bg-apple-gray-50 rounded-lg px-2 py-1">
                <RefreshCw size={12} className={`text-apple-gray-400 ${refreshInterval > 0 ? 'animate-spin' : ''}`} style={refreshInterval > 0 ? { animationDuration: '3s' } : {}} />
                <select
                  value={refreshInterval}
                  onChange={e => setRefreshInterval(Number(e.target.value))}
                  className="text-[11px] bg-transparent text-apple-gray-600 border-none focus:outline-none cursor-pointer"
                >
                  {REFRESH_OPTIONS.map(o => (
                    <option key={o.ms} value={o.ms}>{o.label}</option>
                  ))}
                </select>
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

          {flow && !loading && (
            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-apple-gray-100">
              <span className="text-lg font-bold text-apple-gray-800">{flow.symbol}</span>
              <span className="text-lg font-semibold text-apple-gray-600">${flow.stock_price.toFixed(2)}</span>
              {lastUpdated && (
                <span className="text-[10px] text-apple-gray-400 ml-auto">
                  Updated {Math.round((Date.now() - lastUpdated.getTime()) / 1000)}s ago
                </span>
              )}
            </div>
          )}
        </div>
      </div>

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

      {flow && !loading && (
        <>
          {/* Tab bar */}
          <div className="flex gap-1 bg-white rounded-2xl border border-apple-gray-200 p-1.5">
            {TABS.map(tab => {
              const locked = isTabLocked(tab)
              return (
                <button
                  key={tab.id}
                  onClick={() => !locked && setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-colors flex-1 justify-center ${
                    activeTab === tab.id
                      ? 'bg-apple-blue text-white shadow-sm'
                      : locked
                      ? 'text-apple-gray-300 cursor-not-allowed'
                      : 'text-apple-gray-600 hover:bg-apple-gray-50'
                  }`}
                  title={locked ? `Unlock with ${tab.requiresProvider === 'unusual_whales' ? 'Unusual Whales' : 'Alpha Vantage'}` : ''}
                >
                  {locked ? <Lock size={13} /> : tab.icon}
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              )
            })}
          </div>

          {/* Tab content */}
          <div className="space-y-5">
            {activeTab === 'overview' && (
              <>
                <VerdictBannerV2 flow={flow} beginnerMode={beginnerMode} />
                <PremiumFlow flow={flow} analysis={sa?.premium_analysis ?? null} beginnerMode={beginnerMode} />
                <GreeksPanel flow={flow} analysis={sa?.greeks_analysis ?? null} beginnerMode={beginnerMode} />
                {flow.advanced_greeks && (
                  <GEXPanel greeks={flow.advanced_greeks} stockPrice={flow.stock_price} analysis={sa?.gex_analysis ?? null} beginnerMode={beginnerMode} />
                )}
              </>
            )}

            {activeTab === 'smart_money' && (
              <>
                {flow.unusual_activity.available ? (
                  <>
                    <SweepAlertFeed alerts={flow.flow_alerts || []} analysis={sa?.sweep_analysis ?? null} beginnerMode={beginnerMode} />
                    <SmartMoneyPanel data={flow.smart_money} analysis={sa?.smart_money_analysis ?? null} beginnerMode={beginnerMode} />
                    {flow.dp_correlation && (
                      <DarkPoolPanel dp={flow.dark_pool || []} correlation={flow.dp_correlation} stockPrice={flow.stock_price} analysis={sa?.dark_pool_analysis ?? null} beginnerMode={beginnerMode} />
                    )}
                    {flow.institutional?.trades && flow.institutional.trades.length > 0 && (
                      <InstitutionalPanel trades={flow.institutional.trades} beginnerMode={beginnerMode} />
                    )}
                  </>
                ) : (
                  <ProviderLock provider="Unusual Whales" description="Unlock sweep detection, dark pool prints, and smart money tracking" />
                )}
              </>
            )}

            {activeTab === 'volatility' && (
              <>
                {flow.iv_analysis ? (
                  <IVDashboard iv={flow.iv_analysis} analysis={sa?.iv_analysis ?? null} beginnerMode={beginnerMode} />
                ) : (
                  <ProviderLock provider="Alpha Vantage" description="Unlock IV percentile rank, skew analysis, and term structure" />
                )}
                {flow.advanced_greeks && (
                  <GEXPanel greeks={flow.advanced_greeks} stockPrice={flow.stock_price} analysis={sa?.gex_analysis ?? null} beginnerMode={beginnerMode} />
                )}
              </>
            )}

            {activeTab === 'analysis' && (
              <>
                <StrikeHeatmap heatmap={flow.strike_heatmap} analysis={sa?.strike_analysis ?? null} beginnerMode={beginnerMode} />
                <ExpiryDistributionPanel distribution={flow.expiry_distribution} analysis={sa?.expiry_analysis ?? null} beginnerMode={beginnerMode} />
                <DailyFlowTimeline breakdown={flow.daily_breakdown} arcStatus={flow.arc_status} arcReading={flow.arc_reading} beginnerMode={beginnerMode} />
              </>
            )}

            {activeTab === 'ai_insights' && (
              <>
                <ConvictionV2Panel conviction={flow.conviction_v2} beginnerMode={beginnerMode} />
                <NewsPanel headlines={flow.news_headlines || []} analysis={sa?.news_correlation ?? null} beginnerMode={beginnerMode} />
                <ActionItems analysis={sa?.action_items ?? null} beginnerMode={beginnerMode} />
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}

/* ── Provider Lock Placeholder ──────────────────────────────── */

function ProviderLock({ provider, description }: { provider: string; description: string }) {
  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-8 text-center">
      <Lock size={32} className="mx-auto text-apple-gray-300 mb-3" />
      <h3 className="text-base font-bold text-apple-gray-700 mb-1">Unlock with {provider}</h3>
      <p className="text-sm text-apple-gray-400 max-w-md mx-auto">{description}</p>
      <p className="text-xs text-apple-gray-300 mt-3">Add your API key in Settings to enable these features</p>
    </div>
  )
}

/* ── Verdict Banner V2 (with multi-factor radar) ─────────── */

function VerdictBannerV2({ flow, beginnerMode }: { flow: OptionsFlowV2; beginnerMode: boolean }) {
  const cv2 = flow.conviction_v2
  const hasV2 = cv2 && cv2.factors.length > 0
  const gradient = convictionGradients[hasV2 ? cv2.label : flow.conviction] || 'from-gray-600 to-gray-500'
  const arcBadge = arcStatusColors[flow.arc_status] || 'bg-gray-100 text-gray-600'
  const score = hasV2 ? cv2.score : flow.conviction_score
  const label = hasV2 ? cv2.label : flow.conviction

  return (
    <div className={`bg-gradient-to-r ${gradient} rounded-2xl p-6 text-white shadow-lg`}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="text-4xl font-black">{score}</span>
            <span className="text-lg font-medium text-white/70">/100</span>
          </div>
          <span className="text-lg font-bold">{label}</span>
          {hasV2 && (
            <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
              cv2.confidence === 'high' ? 'bg-white/30' : cv2.confidence === 'medium' ? 'bg-white/20' : 'bg-white/10'
            }`}>
              {cv2.confidence} confidence
            </span>
          )}
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${arcBadge}`}>
            Arc: {flow.arc_status}
          </span>
          {flow.provider_status && (
            <div className="flex gap-1">
              {flow.provider_status.unusual_whales && <span className="text-[9px] bg-white/20 px-1.5 py-0.5 rounded-full">UW</span>}
              {flow.provider_status.alpha_vantage && <span className="text-[9px] bg-white/20 px-1.5 py-0.5 rounded-full">AV</span>}
            </div>
          )}
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

      {/* Factor mini-bars (V2) */}
      {hasV2 && cv2.factors.length > 0 && (
        <div className="mt-4 space-y-1.5">
          {cv2.factors.filter(f => f.available).map((f, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-[10px] text-white/60 w-28 text-right truncate">{f.name}</span>
              <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-white/60 transition-all"
                  style={{ width: `${f.score}%` }}
                />
              </div>
              <span className="text-[10px] text-white/70 w-8 text-right">{f.score}</span>
            </div>
          ))}
        </div>
      )}

      {flow.section_analyses?.flow_summary && (
        <p className="mt-4 text-sm text-white/90 leading-relaxed">{flow.section_analyses.flow_summary}</p>
      )}
      {!flow.section_analyses?.flow_summary && beginnerMode && (
        <p className="mt-4 text-sm text-white/60 italic">Enable LLM for a plain-English flow summary</p>
      )}
    </div>
  )
}

/* ── Premium Flow ────────────────────────────────────────────── */

function PremiumFlow({ flow, analysis, beginnerMode }: { flow: OptionsFlowV2; analysis: string | null; beginnerMode: boolean }) {
  const total = flow.total_call_premium + flow.total_put_premium
  const callPct = total > 0 ? (flow.total_call_premium / total) * 100 : 50
  const putPct = 100 - callPct

  // Intraday flow chart data from UW intervals
  const chartData = (flow.flow_intervals || []).map(d => ({
    time: d.timestamp.slice(0, 19),
    value: d.net_premium,
    color: d.net_premium >= 0 ? '#22c55e' : '#ef4444',
  }))

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

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <BigStatCard label="Call Premium" value={fmtPremium(flow.total_call_premium)} color="text-green-600" icon={<TrendingUp size={18} />} />
        <BigStatCard label="Put Premium" value={fmtPremium(flow.total_put_premium)} color="text-red-600" icon={<TrendingDown size={18} />} />
        <BigStatCard label="C/P Ratio" value={flow.cp_ratio.toFixed(2)} color={flow.cp_ratio >= 1 ? 'text-green-600' : 'text-red-600'} />
        <BigStatCard label="Total Premium" value={fmtPremium(flow.total_premium)} color="text-apple-gray-800" />
      </div>

      {/* Intraday premium chart (UW data) */}
      {chartData.length > 0 && (
        <div className="mt-4">
          <p className="text-xs text-apple-gray-400 font-medium mb-2">Intraday Net Premium (5-min)</p>
          <TimeSeriesChart data={chartData} height={150} />
        </div>
      )}

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

/* ── Greeks & Positioning ────────────────────────────────────── */

function GreeksPanel({ flow, analysis, beginnerMode }: { flow: OptionsFlowV2; analysis: string | null; beginnerMode: boolean }) {
  const g = flow.greeks_summary
  const oi = flow.oi_analysis
  const price = flow.stock_price

  const levels = [g.put_wall, g.max_pain, price, g.call_wall].filter((v): v is number => v != null)
  const min = Math.min(...levels) * 0.995
  const max = Math.max(...levels) * 1.005
  const range = max - min || 1
  const toPos = (v: number) => ((v - min) / range) * 100

  const deltaLabel = g.net_delta > 50000 ? 'Strongly Bullish'
    : g.net_delta > 10000 ? 'Bullish'
    : g.net_delta > -10000 ? 'Neutral'
    : g.net_delta > -50000 ? 'Bearish'
    : 'Strongly Bearish'

  const deltaColor = g.net_delta > 10000 ? 'text-green-600'
    : g.net_delta < -10000 ? 'text-red-600'
    : 'text-gray-600'

  const gammaLabel = g.total_gamma > 100000 ? 'High (dealers will amplify moves)'
    : g.total_gamma > 10000 ? 'Moderate'
    : 'Low (dealers less impactful)'

  const pcrLabel = oi.pcr_oi > 1.2 ? 'Bearish (more puts than calls)'
    : oi.pcr_oi > 0.8 ? 'Neutral balance'
    : 'Bullish (more calls than puts)'

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Shield size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Greeks & Positioning</h3>
        <InfoTooltip
          text="Greeks measure how option prices change. Max Pain = the price where most options expire worthless. Put Wall = support. Call Wall = resistance."
          forceOpen={false}
        />
      </div>

      {g.put_wall != null && g.call_wall != null && g.max_pain != null && (
        <div className="mb-5 px-2">
          <p className="text-xs text-apple-gray-400 mb-2 font-medium">Price Positioning</p>
          <div className="relative h-12 bg-apple-gray-50 rounded-xl">
            <div className="absolute top-5 left-0 right-0 h-1 bg-apple-gray-200 rounded-full" />
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
            <div className="absolute top-0" style={{ left: `${toPos(price)}%`, transform: 'translateX(-50%)' }}>
              <div className="flex flex-col items-center">
                <span className="text-[10px] font-bold text-apple-blue whitespace-nowrap">Price</span>
                <div className="w-0.5 h-3 bg-apple-blue" />
                <div className="w-3.5 h-3.5 rounded-full bg-apple-blue border-2 border-white shadow" />
                <span className="text-[10px] text-apple-blue font-medium mt-0.5">${price.toFixed(2)}</span>
              </div>
            </div>
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

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <GreekDetailCard label="Max Pain" value={g.max_pain != null ? `$${g.max_pain}` : '-'} explanation="Stock prices tend to gravitate toward max pain near expiration." icon={<Target size={16} />} beginnerMode={beginnerMode} />
        <GreekDetailCard label="Put Wall (Support)" value={g.put_wall != null ? `$${g.put_wall}` : '-'} explanation="Strike with most put OI — acts as support." color="text-red-600" icon={<Shield size={16} />} beginnerMode={beginnerMode} />
        <GreekDetailCard label="Call Wall (Resistance)" value={g.call_wall != null ? `$${g.call_wall}` : '-'} explanation="Strike with most call OI — acts as resistance." color="text-green-600" icon={<Shield size={16} />} beginnerMode={beginnerMode} />
        <GreekDetailCard label="Net Delta" value={g.net_delta != null ? `${g.net_delta > 0 ? '+' : ''}${g.net_delta.toLocaleString()}` : '-'} subtitle={deltaLabel} explanation="Aggregate directional bet across all options." color={deltaColor} icon={<Gauge size={16} />} beginnerMode={beginnerMode} />
        <GreekDetailCard label="Total Gamma" value={g.total_gamma != null ? g.total_gamma.toLocaleString() : '-'} subtitle={gammaLabel} explanation="High gamma means market makers hedge aggressively." icon={<Activity size={16} />} beginnerMode={beginnerMode} />
        <GreekDetailCard label="Put/Call OI Ratio" value={oi.pcr_oi.toFixed(2)} subtitle={pcrLabel} explanation="Above 1.0 = more puts (bearish). Below 0.7 = more calls (bullish)." icon={<BarChart3 size={16} />} beginnerMode={beginnerMode} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="bg-green-50 rounded-xl p-3 text-center">
          <p className="text-xs text-green-600 font-medium">Total Call OI</p>
          <p className="text-xl font-bold text-green-700">{oi.total_call_oi.toLocaleString()}</p>
        </div>
        <div className="bg-red-50 rounded-xl p-3 text-center">
          <p className="text-xs text-red-600 font-medium">Total Put OI</p>
          <p className="text-xl font-bold text-red-700">{oi.total_put_oi.toLocaleString()}</p>
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

/* ── GEX Panel ───────────────────────────────────────────────── */

function GEXPanel({ greeks, stockPrice, analysis, beginnerMode }: {
  greeks: NonNullable<OptionsFlowV2['advanced_greeks']>
  stockPrice: number
  analysis: string | null
  beginnerMode: boolean
}) {
  const maxGex = Math.max(...greeks.gex_by_strike.map(g => Math.abs(g.gex)), 1)

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Activity size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Gamma Exposure (GEX)</h3>
        <InfoTooltip
          text="GEX shows how market makers must hedge. Positive GEX = mean-reversion (dealers dampen moves). Negative GEX = momentum (dealers amplify moves). The flip level is where the regime changes."
          forceOpen={false}
        />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className={`rounded-xl p-3 text-center ${greeks.gex_regime === 'positive' ? 'bg-blue-50' : 'bg-orange-50'}`}>
          <p className="text-[10px] text-apple-gray-400 font-medium">GEX Regime</p>
          <p className={`text-sm font-bold ${greeks.gex_regime === 'positive' ? 'text-blue-700' : 'text-orange-700'}`}>
            {greeks.gex_regime === 'positive' ? 'Mean-Reversion' : 'Momentum'}
          </p>
        </div>
        <div className="bg-apple-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-apple-gray-400 font-medium">GEX Flip Level</p>
          <p className="text-sm font-bold text-apple-gray-800">
            {greeks.gex_flip_level ? `$${greeks.gex_flip_level}` : '-'}
          </p>
        </div>
        <div className="bg-apple-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-apple-gray-400 font-medium">Total DEX</p>
          <p className="text-sm font-bold text-apple-gray-800">{fmtPremium(greeks.total_dex)}</p>
        </div>
      </div>

      {beginnerMode && (
        <p className="text-[10px] text-apple-gray-400 mb-3">{greeks.gex_description}</p>
      )}

      {/* GEX by strike bar chart */}
      {greeks.gex_by_strike.length > 0 && (
        <div className="space-y-1">
          {greeks.gex_by_strike.slice(0, 15).map((g, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-[10px] text-apple-gray-500 w-16 text-right">${g.strike}</span>
              <div className="flex-1 flex items-center">
                {g.gex < 0 && (
                  <div className="flex-1 flex justify-end">
                    <div className="h-4 bg-orange-300 rounded-l" style={{ width: `${(Math.abs(g.gex) / maxGex) * 50}%` }} />
                  </div>
                )}
                {g.gex < 0 && <div className="w-px h-6 bg-apple-gray-300" />}
                {g.gex >= 0 && <div className="flex-1" />}
                {g.gex >= 0 && <div className="w-px h-6 bg-apple-gray-300" />}
                {g.gex >= 0 && (
                  <div className="flex-1">
                    <div className="h-4 bg-blue-300 rounded-r" style={{ width: `${(Math.abs(g.gex) / maxGex) * 50}%` }} />
                  </div>
                )}
                {g.gex < 0 && <div className="flex-1" />}
              </div>
            </div>
          ))}
          {greeks.gex_flip_level && (
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[10px] text-amber-600 w-16 text-right font-bold">Flip</span>
              <div className="flex-1 border-t-2 border-dashed border-amber-400" />
              <span className="text-[10px] text-amber-600 font-bold">${greeks.gex_flip_level}</span>
            </div>
          )}
        </div>
      )}

      <LLMAnalysisPanel analysis={analysis} defaultOpen={beginnerMode} />
    </div>
  )
}

/* ── Sweep Alert Feed ────────────────────────────────────────── */

function SweepAlertFeed({ alerts, analysis, beginnerMode }: { alerts: FlowAlert[]; analysis: string | null; beginnerMode: boolean }) {
  const [filter, setFilter] = useState<string>('all')

  const filtered = alerts.filter(a => {
    if (filter === 'all') return true
    if (filter === 'sweeps') return a.type === 'sweep' || a.type === 'golden_sweep'
    if (filter === 'blocks') return a.type === 'block'
    if (filter === 'golden') return a.type === 'golden_sweep'
    return true
  })

  const typeStyle: Record<string, string> = {
    golden_sweep: 'bg-amber-100 text-amber-800 border-amber-300',
    sweep: 'bg-purple-50 text-purple-700 border-purple-200',
    block: 'bg-blue-50 text-blue-700 border-blue-200',
    trade: 'bg-gray-50 text-gray-600 border-gray-200',
  }

  const typeLabel: Record<string, string> = {
    golden_sweep: 'GOLDEN',
    sweep: 'SWEEP',
    block: 'BLOCK',
    trade: 'TRADE',
  }

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Zap size={18} className="text-amber-500" />
          <h3 className="text-base font-bold text-apple-gray-800">Sweep & Block Feed</h3>
          <InfoTooltip
            text="Sweeps are large orders split across exchanges (smart money). Blocks are single large fills. Golden sweeps hit the ask aggressively, showing highest conviction."
            forceOpen={false}
          />
        </div>
        <div className="flex gap-1">
          {['all', 'sweeps', 'blocks', 'golden'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`text-[10px] px-2 py-1 rounded-lg font-medium ${
                filter === f ? 'bg-apple-blue text-white' : 'bg-apple-gray-50 text-apple-gray-500'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {filtered.length > 0 ? (
        <div className="space-y-1.5 max-h-96 overflow-y-auto">
          {filtered.map((a, i) => (
            <div key={i} className={`flex items-center gap-3 p-2.5 rounded-xl border ${typeStyle[a.type] || typeStyle.trade}`}>
              <span className="text-[9px] font-black tracking-wider w-14">{typeLabel[a.type] || 'TRADE'}</span>
              <span className={`text-xs font-bold ${a.sentiment === 'bullish' ? 'text-green-600' : a.sentiment === 'bearish' ? 'text-red-600' : 'text-gray-600'}`}>
                {a.side}
              </span>
              <span className="text-xs text-apple-gray-600">${a.strike}</span>
              <span className="text-[10px] text-apple-gray-400">{a.expiry}</span>
              <span className="text-xs font-bold text-apple-gray-800 ml-auto">{fmtPremium(a.premium)}</span>
              {a.ask_side_pct != null && (
                <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${a.ask_side_pct >= 0.7 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  {(a.ask_side_pct * 100).toFixed(0)}% ask
                </span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-apple-gray-400 text-center py-6">No alerts matching filter</p>
      )}

      <LLMAnalysisPanel analysis={analysis} defaultOpen={beginnerMode} />
    </div>
  )
}

/* ── Smart Money vs Retail ───────────────────────────────────── */

function SmartMoneyPanel({ data, analysis, beginnerMode }: {
  data: OptionsFlowV2['smart_money']
  analysis: string | null
  beginnerMode: boolean
}) {
  if (!data.available) return null

  const divergenceColor = data.divergence_score >= 50 ? 'text-red-600' : data.divergence_score >= 25 ? 'text-amber-600' : 'text-green-600'
  const divergenceLabel = data.divergence_score >= 50 ? 'HIGH DIVERGENCE' : data.divergence_score >= 25 ? 'Moderate' : 'Aligned'

  const sentColor = (s: string) => s === 'bullish' ? 'text-green-600' : s === 'bearish' ? 'text-red-600' : 'text-gray-600'

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Users size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Smart Money vs Retail</h3>
        <InfoTooltip
          text="Smart money = sweeps, blocks, large premiums. Retail = small trades. When they disagree (divergence), smart money usually wins."
          forceOpen={false}
        />
      </div>

      {/* Donut-style split bar */}
      <div className="flex rounded-full overflow-hidden h-8 mb-4">
        <div
          className="bg-indigo-500 flex items-center justify-center text-[11px] font-bold text-white"
          style={{ width: `${data.smart_money_pct}%` }}
        >
          {data.smart_money_pct >= 20 && `${data.smart_money_pct.toFixed(0)}% Smart`}
        </div>
        <div
          className="bg-gray-300 flex items-center justify-center text-[11px] font-bold text-gray-700"
          style={{ width: `${data.retail_pct}%` }}
        >
          {data.retail_pct >= 20 && `${data.retail_pct.toFixed(0)}% Retail`}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="bg-indigo-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-indigo-400 font-medium">Smart Money</p>
          <p className={`text-lg font-bold ${sentColor(data.smart_money_sentiment)}`}>
            {data.smart_money_sentiment}
          </p>
        </div>
        <div className="bg-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-gray-400 font-medium">Retail</p>
          <p className={`text-lg font-bold ${sentColor(data.retail_sentiment)}`}>
            {data.retail_sentiment}
          </p>
        </div>
        <div className={`rounded-xl p-3 text-center ${data.divergence_score >= 50 ? 'bg-red-50' : 'bg-apple-gray-50'}`}>
          <p className="text-[10px] text-apple-gray-400 font-medium">Divergence</p>
          <p className={`text-2xl font-black ${divergenceColor}`}>{data.divergence_score}</p>
          <p className={`text-[10px] font-medium ${divergenceColor}`}>{divergenceLabel}</p>
        </div>
      </div>

      {beginnerMode && data.divergence_score >= 50 && (
        <div className="mt-3 p-2 bg-red-50 rounded-lg">
          <p className="text-[10px] text-red-600">Smart money and retail disagree. Historically, smart money (sweeps/blocks) tends to be right. Watch for the price to follow smart money direction.</p>
        </div>
      )}

      <LLMAnalysisPanel analysis={analysis} defaultOpen={beginnerMode} />
    </div>
  )
}

/* ── Dark Pool Panel ─────────────────────────────────────────── */

function DarkPoolPanel({ dp, correlation, stockPrice, analysis, beginnerMode }: {
  dp: NonNullable<OptionsFlowV2['dark_pool']>
  correlation: NonNullable<OptionsFlowV2['dp_correlation']>
  stockPrice: number
  analysis: string | null
  beginnerMode: boolean
}) {
  const sentColor = correlation.dp_sentiment === 'bullish' ? 'text-green-600' : correlation.dp_sentiment === 'bearish' ? 'text-red-600' : 'text-gray-600'

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Eye size={18} className="text-purple-500" />
        <h3 className="text-base font-bold text-apple-gray-800">Dark Pool Activity</h3>
        <InfoTooltip
          text="Dark pools are private exchanges where institutions trade. Prints above spot price suggest institutional buying. High notional volume shows conviction."
          forceOpen={false}
        />
      </div>

      <div className="grid grid-cols-4 gap-3 mb-4">
        <div className="bg-apple-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-apple-gray-400">Total Prints</p>
          <p className="text-lg font-bold text-apple-gray-800">{correlation.total_prints}</p>
        </div>
        <div className="bg-apple-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-apple-gray-400">Total Notional</p>
          <p className="text-lg font-bold text-apple-gray-800">{fmtPremium(correlation.total_notional)}</p>
        </div>
        <div className="bg-apple-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-apple-gray-400">vs Spot</p>
          <p className={`text-lg font-bold ${correlation.price_vs_spot_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {correlation.price_vs_spot_pct >= 0 ? '+' : ''}{correlation.price_vs_spot_pct}%
          </p>
        </div>
        <div className="bg-apple-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-apple-gray-400">DP Sentiment</p>
          <p className={`text-lg font-bold ${sentColor}`}>{correlation.dp_sentiment}</p>
        </div>
      </div>

      {/* Above/below spot visualization */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] text-green-500 font-medium">Above: {correlation.above_spot}</span>
        <div className="flex-1 flex rounded-full overflow-hidden h-3">
          <div className="bg-green-400" style={{ width: `${correlation.total_prints > 0 ? (correlation.above_spot / correlation.total_prints) * 100 : 50}%` }} />
          <div className="bg-red-400" style={{ width: `${correlation.total_prints > 0 ? (correlation.below_spot / correlation.total_prints) * 100 : 50}%` }} />
        </div>
        <span className="text-[10px] text-red-500 font-medium">Below: {correlation.below_spot}</span>
      </div>

      {/* DP prints list */}
      {dp.length > 0 && (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {dp.slice(0, 10).map((d, i) => (
            <div key={i} className="flex items-center gap-3 text-xs p-2 rounded-lg bg-apple-gray-50">
              <span className={`font-bold ${d.price > stockPrice ? 'text-green-600' : 'text-red-600'}`}>
                ${d.price.toFixed(2)}
              </span>
              <span className="text-apple-gray-400">{d.size.toLocaleString()} shares</span>
              <span className="text-apple-gray-500 ml-auto">{fmtPremium(d.notional)}</span>
              {d.exchange && <span className="text-[9px] text-apple-gray-300">{d.exchange}</span>}
            </div>
          ))}
        </div>
      )}

      <LLMAnalysisPanel analysis={analysis} defaultOpen={beginnerMode} />
    </div>
  )
}

/* ── Institutional Panel ──────────────────────────────────────── */

function InstitutionalPanel({ trades, beginnerMode }: {
  trades: NonNullable<OptionsFlowV2['institutional']>['trades']
  beginnerMode: boolean
}) {
  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Shield size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Institutional Activity</h3>
        <InfoTooltip
          text="Congress and insider trades reported publicly. These can signal informed views about a company's prospects."
          forceOpen={false}
        />
      </div>

      <div className="space-y-1.5">
        {trades.map((t, i) => {
          const isBuy = (t.type || '').toLowerCase().includes('buy') || (t.type || '').toLowerCase().includes('purchase')
          return (
            <div key={i} className={`flex items-center gap-3 p-2.5 rounded-xl ${isBuy ? 'bg-green-50' : 'bg-red-50'}`}>
              <span className={`text-[10px] font-bold ${isBuy ? 'text-green-600' : 'text-red-600'}`}>
                {t.type || 'Trade'}
              </span>
              <span className="text-xs text-apple-gray-700 font-medium flex-1">{t.name}</span>
              <span className="text-xs text-apple-gray-500">{t.amount}</span>
              <span className="text-[10px] text-apple-gray-400">{t.date}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── IV Dashboard ────────────────────────────────────────────── */

function IVDashboard({ iv, analysis, beginnerMode }: {
  iv: NonNullable<OptionsFlowV2['iv_analysis']>
  analysis: string | null
  beginnerMode: boolean
}) {
  const ivColor = (iv.iv_percentile ?? 50) > 70 ? 'text-red-600' : (iv.iv_percentile ?? 50) < 30 ? 'text-green-600' : 'text-amber-600'
  const skewLabel = iv.iv_skew > 0.02 ? 'Put Skew (downside priced)' : iv.iv_skew < -0.02 ? 'Call Skew (upside priced)' : 'Balanced'

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Activity size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">IV Dashboard</h3>
        <InfoTooltip
          text="IV (Implied Volatility) shows how expensive options are. Low IV percentile = cheap options. High = expensive. IV skew shows whether puts or calls are pricier."
          forceOpen={false}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="bg-apple-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-apple-gray-400">Current IV</p>
          <p className="text-xl font-bold text-apple-gray-800">{(iv.current_iv * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-apple-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-apple-gray-400">IV Percentile</p>
          <p className={`text-xl font-bold ${ivColor}`}>
            {iv.iv_percentile != null ? `${iv.iv_percentile.toFixed(0)}%` : '-'}
          </p>
          {beginnerMode && (
            <p className="text-[9px] text-apple-gray-400 mt-0.5">
              {(iv.iv_percentile ?? 50) > 70 ? 'Expensive' : (iv.iv_percentile ?? 50) < 30 ? 'Cheap' : 'Fair'}
            </p>
          )}
        </div>
        <div className="bg-apple-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-apple-gray-400">IV Skew</p>
          <p className={`text-lg font-bold ${iv.iv_skew > 0.02 ? 'text-red-600' : iv.iv_skew < -0.02 ? 'text-green-600' : 'text-gray-600'}`}>
            {(iv.iv_skew * 100).toFixed(1)}%
          </p>
          <p className="text-[9px] text-apple-gray-400 mt-0.5">{skewLabel}</p>
        </div>
        <div className={`rounded-xl p-3 text-center ${iv.crush_risk ? 'bg-red-50' : 'bg-apple-gray-50'}`}>
          <p className="text-[10px] text-apple-gray-400">Crush Risk</p>
          <p className={`text-lg font-bold ${iv.crush_risk ? 'text-red-600' : 'text-green-600'}`}>
            {iv.crush_risk ? 'YES' : 'Low'}
          </p>
        </div>
      </div>

      {/* Term structure */}
      <div className="bg-apple-gray-50 rounded-xl p-3">
        <p className="text-[10px] text-apple-gray-400 font-medium mb-2">Term Structure</p>
        <div className="flex items-end gap-6">
          <div className="text-center">
            <div className="h-16 flex items-end justify-center">
              <div className="w-12 bg-blue-400 rounded-t" style={{ height: `${Math.min(iv.near_term_iv / Math.max(iv.near_term_iv, iv.far_term_iv, 0.01) * 100, 100)}%` }} />
            </div>
            <p className="text-[10px] text-apple-gray-500 mt-1">Near: {(iv.near_term_iv * 100).toFixed(1)}%</p>
          </div>
          <div className="text-center">
            <div className="h-16 flex items-end justify-center">
              <div className="w-12 bg-indigo-400 rounded-t" style={{ height: `${Math.min(iv.far_term_iv / Math.max(iv.near_term_iv, iv.far_term_iv, 0.01) * 100, 100)}%` }} />
            </div>
            <p className="text-[10px] text-apple-gray-500 mt-1">Far: {(iv.far_term_iv * 100).toFixed(1)}%</p>
          </div>
          <div className="flex-1">
            <span className={`text-xs font-medium px-2 py-1 rounded-full ${
              iv.term_structure === 'inverted' ? 'bg-red-100 text-red-700' :
              iv.term_structure === 'contango' ? 'bg-green-100 text-green-700' :
              'bg-gray-100 text-gray-600'
            }`}>
              {iv.term_structure === 'inverted' ? 'Inverted (event expected)' :
               iv.term_structure === 'contango' ? 'Normal (contango)' : 'Flat'}
            </span>
          </div>
        </div>
      </div>

      {/* Call/Put IV comparison */}
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div className="bg-green-50 rounded-xl p-2 text-center">
          <p className="text-[10px] text-green-500">Avg Call IV</p>
          <p className="text-sm font-bold text-green-700">{(iv.avg_call_iv * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-red-50 rounded-xl p-2 text-center">
          <p className="text-[10px] text-red-500">Avg Put IV</p>
          <p className="text-sm font-bold text-red-700">{(iv.avg_put_iv * 100).toFixed(1)}%</p>
        </div>
      </div>

      <LLMAnalysisPanel analysis={analysis} defaultOpen={beginnerMode} />
    </div>
  )
}

/* ── Conviction V2 Panel ──────────────────────────────────────── */

function ConvictionV2Panel({ conviction, beginnerMode }: {
  conviction: OptionsFlowV2['conviction_v2']
  beginnerMode: boolean
}) {
  if (!conviction || conviction.factors.length === 0) return null

  const scoreColor = conviction.score >= 65 ? 'text-green-600' : conviction.score >= 45 ? 'text-amber-600' : 'text-red-600'
  const confBadge = conviction.confidence === 'high' ? 'bg-green-100 text-green-700' :
    conviction.confidence === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Gauge size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Conviction V2 Breakdown</h3>
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${confBadge}`}>
          {conviction.confidence} confidence
        </span>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <div className="text-center">
          <p className={`text-4xl font-black ${scoreColor}`}>{conviction.score}</p>
          <p className={`text-sm font-bold ${scoreColor}`}>{conviction.label}</p>
        </div>
        <div className="flex-1 text-xs text-apple-gray-400">
          {conviction.available_factors}/{conviction.total_factors} factors available
        </div>
      </div>

      <div className="space-y-2">
        {conviction.factors.map((f, i) => (
          <div key={i} className={`flex items-center gap-3 p-2 rounded-lg ${f.available ? 'bg-apple-gray-50' : 'bg-gray-50 opacity-50'}`}>
            <div className="w-28 shrink-0">
              <p className="text-xs font-medium text-apple-gray-700">{f.name}</p>
              <p className="text-[9px] text-apple-gray-400">{f.source}</p>
            </div>
            <div className="flex-1 h-2 bg-apple-gray-200 rounded-full overflow-hidden">
              {f.available && (
                <div
                  className={`h-full rounded-full ${f.score >= 65 ? 'bg-green-400' : f.score >= 45 ? 'bg-amber-400' : 'bg-red-400'}`}
                  style={{ width: `${f.score}%` }}
                />
              )}
            </div>
            <span className="text-xs font-bold text-apple-gray-600 w-8 text-right">
              {f.available ? f.score : '-'}
            </span>
            <span className="text-[9px] text-apple-gray-400 w-20 text-right truncate">{f.detail}</span>
          </div>
        ))}
      </div>

      {beginnerMode && (
        <p className="text-[10px] text-apple-gray-400 mt-3">
          Conviction V2 combines {conviction.total_factors} factors from multiple data providers.
          Missing providers are excluded and weights redistributed to available factors.
        </p>
      )}
    </div>
  )
}

/* ── Strike Heatmap ──────────────────────────────────────────── */

function StrikeHeatmap({ heatmap, analysis, beginnerMode }: { heatmap: StrikeHeatmapEntry[]; analysis: string | null; beginnerMode: boolean }) {
  if (!heatmap.length) return null
  const maxPrem = Math.max(...heatmap.map(h => Math.max(h.call_premium, h.put_premium)))

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Target size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Strike Heatmap</h3>
        <InfoTooltip text="Strikes with highest premium = biggest bets. Green = calls, Red = puts." forceOpen={false} />
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
                  <div className="h-6 bg-red-300 rounded-l transition-all" style={{ width: `${putWidth}%` }} />
                </div>
                <div className="w-20 text-center shrink-0">
                  <span className={`text-xs font-bold ${isTop3 ? 'text-amber-700' : 'text-apple-gray-700'}`}>${h.strike}</span>
                </div>
                <div className="flex-1">
                  <div className="h-6 bg-green-300 rounded-r transition-all" style={{ width: `${callWidth}%` }} />
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

/* ── Expiry Distribution ─────────────────────────────────────── */

function ExpiryDistributionPanel({ distribution, analysis, beginnerMode }: { distribution: ExpiryDistribution[]; analysis: string | null; beginnerMode: boolean }) {
  if (!distribution.length) return null
  const maxPrem = Math.max(...distribution.map(d => d.total_premium))
  const expiryColor = (days: number) => days < 7 ? 'bg-red-400' : days < 30 ? 'bg-amber-400' : 'bg-blue-400'

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Clock size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">Expiry Distribution</h3>
        <InfoTooltip text="Near-term expiries (red) = urgent conviction. Far dates (blue) = strategic bets." forceOpen={false} />
      </div>
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
              <p className="text-[10px] text-apple-gray-400">{d.days_to_expiry}d{d.top_strike ? ` | Top: $${d.top_strike}` : ''}</p>
            </div>
            <div className="flex-1 h-6 bg-apple-gray-50 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all ${expiryColor(d.days_to_expiry)}`} style={{ width: `${maxPrem > 0 ? (d.total_premium / maxPrem) * 100 : 0}%` }} />
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

/* ── Daily Flow Timeline ─────────────────────────────────────── */

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
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${arcBadge}`}>Arc: {arcStatus}</span>
      </div>

      {breakdown.length < 2 ? (
        <p className="text-xs text-apple-gray-400 text-center py-6">Daily history builds automatically. Check back tomorrow for trend data.</p>
      ) : (
        <>
          <div className="flex items-end gap-1 mb-4 h-16 px-2">
            {[...breakdown].reverse().map((d, i) => {
              const maxRatio = Math.max(...breakdown.map(b => b.cp_ratio))
              const height = maxRatio > 0 ? (d.cp_ratio / maxRatio) * 100 : 50
              const barColor = d.cp_ratio >= 1.5 ? 'bg-green-400' : d.cp_ratio >= 0.8 ? 'bg-gray-300' : 'bg-red-400'
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                  <span className="text-[9px] text-apple-gray-400">{d.cp_ratio.toFixed(1)}</span>
                  <div className={`w-full rounded-t ${barColor}`} style={{ height: `${height}%` }} />
                </div>
              )
            })}
          </div>
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
                  <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full mt-1.5 ${badge}`}>{d.sentiment}</span>
                </div>
              )
            })}
          </div>
        </>
      )}

      {arcReading && (
        <div className="mt-4 p-3 bg-indigo-50 rounded-xl">
          <p className="text-xs text-indigo-900/80 leading-relaxed">{arcReading}</p>
        </div>
      )}
    </div>
  )
}

/* ── News & Correlation ──────────────────────────────────────── */

function NewsPanel({ headlines, analysis, beginnerMode }: { headlines: NewsHeadline[]; analysis: string | null; beginnerMode: boolean }) {
  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Newspaper size={18} className="text-apple-blue" />
        <h3 className="text-base font-bold text-apple-gray-800">News & Correlation</h3>
      </div>
      {headlines.length > 0 ? (
        <div className="space-y-2.5">
          {headlines.map((h, i) => (
            <a key={i} href={h.url || '#'} target="_blank" rel="noopener noreferrer" className="block bg-apple-gray-50 rounded-xl p-3.5 hover:bg-apple-gray-100 transition-colors group">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-apple-gray-800 group-hover:text-apple-blue transition-colors line-clamp-2">{h.title}</p>
                  {h.description && <p className="text-xs text-apple-gray-400 mt-1 line-clamp-1">{h.description}</p>}
                  <div className="flex items-center gap-2 mt-1.5">
                    {h.source && <span className="text-[10px] text-apple-gray-400">{h.source}</span>}
                    {h.published_at && <span className="text-[10px] text-apple-gray-300">{new Date(h.published_at).toLocaleDateString()}</span>}
                  </div>
                </div>
                {h.url && <ExternalLink size={14} className="text-apple-gray-300 group-hover:text-apple-blue shrink-0 mt-0.5" />}
              </div>
            </a>
          ))}
        </div>
      ) : (
        <p className="text-xs text-apple-gray-400 text-center py-4">No recent news found.</p>
      )}
      <LLMAnalysisPanel analysis={analysis} defaultOpen={beginnerMode} />
    </div>
  )
}

/* ── Action Items ────────────────────────────────────────────── */

function ActionItems({ analysis, beginnerMode }: { analysis: string | null; beginnerMode: boolean }) {
  const items = analysis ? analysis.split(/\n/).filter(line => /^\d+[\.\)]/.test(line.trim())) : []

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
        <InfoTooltip text="AI-generated suggestions based on options data. Not financial advice." forceOpen={false} />
      </div>
      {items.length > 0 ? (
        <div className="space-y-2.5">
          {items.map((item, i) => {
            const sentiment = getItemSentiment(item)
            return (
              <div key={i} className={`border-l-4 rounded-r-xl p-3.5 ${sentimentStyle[sentiment]}`}>
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
        <p className="text-xs text-apple-gray-400 text-center py-4">Enable LLM for AI-generated action items</p>
      )}
      {beginnerMode && (
        <p className="text-[10px] text-apple-gray-400 mt-3 text-center">These are AI-generated observations. Not financial advice.</p>
      )}
    </div>
  )
}
