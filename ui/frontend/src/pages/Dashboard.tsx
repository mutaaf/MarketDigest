import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  RefreshCw, Play, AlertCircle, Sun, Sunset, Calendar,
  Target, TrendingUp, TrendingDown, Activity, Award, ChevronRight,
  BarChart3
} from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import api from '../api/client'
import type { ApiStatus, MarketIndex, OptionsConvictionEntry } from '../api/types'
import StatusDot from '../components/common/StatusDot'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ToastContainer from '../components/common/Toast'

const DIGEST_TYPES = [
  { key: 'morning', label: 'Morning', icon: Sun, desc: 'Pre-market analysis', color: 'text-amber-500', bg: 'bg-amber-500/10' },
  { key: 'afternoon', label: 'Afternoon', icon: Sunset, desc: 'Close & recap', color: 'text-orange-500', bg: 'bg-orange-500/10' },
  { key: 'weekly', label: 'Weekly', icon: Calendar, desc: 'Week in review', color: 'text-blue-500', bg: 'bg-blue-500/10' },
  { key: 'daytrade', label: 'Day Trade', icon: Target, desc: 'Ranked picks', color: 'text-green-500', bg: 'bg-green-500/10' },
  { key: 'options', label: 'Options', icon: Activity, desc: 'Top 3 convictions', color: 'text-purple-500', bg: 'bg-purple-500/10' },
]

function MarketCard({ label, data }: { label: string; data?: MarketIndex }) {
  if (!data) return (
    <div className="card !p-4">
      <p className="text-xs text-apple-gray-400 uppercase tracking-wide">{label}</p>
      <p className="text-lg text-apple-gray-300 mt-1">--</p>
    </div>
  )

  const isUp = data.change_pct >= 0
  const isVix = label === 'VIX'
  // For VIX, up is bearish (red), down is bullish (green)
  const colorClass = isVix
    ? (isUp ? 'text-red-500' : 'text-green-500')
    : (isUp ? 'text-green-500' : 'text-red-500')

  return (
    <div className="card !p-4">
      <p className="text-xs text-apple-gray-400 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold mt-1">
        {label === 'VIX' ? data.price.toFixed(1) : data.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </p>
      <div className={`flex items-center gap-1 text-sm ${colorClass}`}>
        {isUp ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
        <span>{isUp ? '+' : ''}{data.change_pct.toFixed(2)}%</span>
      </div>
    </div>
  )
}

function ConvictionBadge({ conviction, score }: { conviction: string; score: number }) {
  const colors: Record<string, string> = {
    'Extreme Bull': 'bg-green-100 text-green-700',
    'Strong Bull': 'bg-green-100 text-green-700',
    'Bull': 'bg-green-50 text-green-600',
    'Neutral': 'bg-gray-100 text-gray-600',
    'Bear': 'bg-red-50 text-red-600',
    'Strong Bear': 'bg-red-100 text-red-700',
    'Extreme Bear': 'bg-red-100 text-red-700',
  }
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${colors[conviction] || 'bg-gray-100 text-gray-600'}`}>
      {conviction} ({score})
    </span>
  )
}

function ConvictionRow({ entry }: { entry: OptionsConvictionEntry }) {
  const barWidth = Math.min(entry.conviction_score, 100)
  const barColor = entry.conviction_score >= 65 ? 'bg-green-400' : entry.conviction_score >= 40 ? 'bg-gray-400' : 'bg-red-400'

  return (
    <div className="flex items-center gap-3 py-2">
      <span className="font-medium text-sm w-14">{entry.symbol}</span>
      <div className="flex-1">
        <div className="h-2 bg-apple-gray-100 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${barColor}`} style={{ width: `${barWidth}%` }} />
        </div>
      </div>
      <span className="text-xs text-apple-gray-400 w-12 text-right">C/P {entry.cp_ratio.toFixed(1)}</span>
      <ConvictionBadge conviction={entry.conviction} score={entry.conviction_score} />
    </div>
  )
}

export default function Dashboard() {
  const { data: status, loading, refetch } = useApi<ApiStatus>('/status')
  const { toasts, addToast, removeToast } = useToast()
  const [runningDigest, setRunningDigest] = useState<string | null>(null)
  const [showAllApis, setShowAllApis] = useState(false)
  const navigate = useNavigate()

  const runQuickDigest = async (type: string) => {
    setRunningDigest(type)
    try {
      const res = await api.post('/digests/run', { digest_type: type, mode: 'facts', dry_run: true })
      if (res.data.success) {
        addToast(`${type} digest generated (${res.data.message_count} messages)`, 'success')
        navigate('/run', { state: { content: res.data.content, type } })
      }
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Digest run failed', 'error')
    } finally {
      setRunningDigest(null)
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />

  if (!status) return (
    <div className="flex items-center gap-3 text-apple-red mt-20 justify-center">
      <AlertCircle size={20} />
      <span>Failed to load status</span>
    </div>
  )

  if (!status.onboarding_complete) {
    return (
      <div className="max-w-lg mx-auto mt-20 text-center">
        <h2 className="text-2xl font-semibold mb-4">Welcome to Market Digest</h2>
        <p className="text-apple-gray-500 mb-6">
          Let's set up your API keys and configure your first digest.
        </p>
        <button onClick={() => navigate('/onboarding')} className="btn-primary text-base px-8 py-3">
          Start Setup
        </button>
      </div>
    )
  }

  const apiEntries = Object.entries(status.apis)
  const configuredCount = apiEntries.filter(([, info]) => info.configured).length
  const ms = status.market_snapshot

  return (
    <div className="max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Command Center</h1>
          <p className="text-apple-gray-400 text-sm mt-1">Market overview and quick actions</p>
        </div>
        <button onClick={refetch} className="btn-secondary flex items-center gap-2">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Row 1: Market Snapshot */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <MarketCard label="S&P 500" data={ms?.spy} />
        <MarketCard label="NASDAQ" data={ms?.qqq} />
        <MarketCard label="VIX" data={ms?.vix} />
      </div>

      {/* Row 2: Quick Actions - 5 digest types */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
        {DIGEST_TYPES.map(({ key, label, icon: Icon, desc, color, bg }) => (
          <button
            key={key}
            onClick={() => runQuickDigest(key)}
            disabled={runningDigest !== null}
            className="card !p-4 hover:border-apple-blue transition-colors text-left group"
          >
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center group-hover:scale-110 transition-transform`}>
                {runningDigest === key
                  ? <LoadingSpinner size="sm" />
                  : <Icon size={16} className={color} />
                }
              </div>
            </div>
            <p className="font-medium text-sm">{label}</p>
            <p className="text-[11px] text-apple-gray-400">{desc}</p>
          </button>
        ))}
      </div>

      {/* Row 3: Two-column — Options Conviction + Retrace Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Options Conviction Panel */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-purple-500" />
              <h3 className="text-sm font-medium text-apple-gray-800">Options Flow Conviction</h3>
            </div>
            <button
              onClick={() => navigate('/options')}
              className="text-xs text-apple-blue flex items-center gap-1 hover:underline"
            >
              View All <ChevronRight size={12} />
            </button>
          </div>
          {status.options_conviction && status.options_conviction.length > 0 ? (
            <div className="divide-y divide-apple-gray-100">
              {status.options_conviction.map((entry) => (
                <ConvictionRow key={entry.symbol} entry={entry} />
              ))}
            </div>
          ) : (
            <div className="text-center py-6">
              <Activity size={24} className="text-apple-gray-300 mx-auto mb-2" />
              <p className="text-sm text-apple-gray-400">No options data yet</p>
              <button
                onClick={() => runQuickDigest('options')}
                disabled={runningDigest !== null}
                className="text-xs text-apple-blue mt-2 hover:underline"
              >
                Run options digest to populate
              </button>
            </div>
          )}
        </div>

        {/* Retrace Performance Panel */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Award size={16} className="text-amber-500" />
              <h3 className="text-sm font-medium text-apple-gray-800">Pick Performance</h3>
            </div>
            <button
              onClick={() => navigate('/retrace')}
              className="text-xs text-apple-blue flex items-center gap-1 hover:underline"
            >
              Details <ChevronRight size={12} />
            </button>
          </div>
          {status.retrace_summary ? (
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-2xl font-semibold text-green-500">
                  {status.retrace_summary.win_rate.toFixed(0)}%
                </p>
                <p className="text-[11px] text-apple-gray-400">Win Rate</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-semibold">
                  {status.retrace_summary.avg_r !== null ? `${status.retrace_summary.avg_r.toFixed(1)}R` : '--'}
                </p>
                <p className="text-[11px] text-apple-gray-400">Avg R</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-semibold">{status.retrace_summary.total_graded}</p>
                <p className="text-[11px] text-apple-gray-400">Picks Graded</p>
              </div>
              <div className="col-span-3 text-center">
                <p className="text-xs text-apple-gray-400">
                  Across {status.retrace_summary.days_tracked} trading days
                </p>
              </div>
            </div>
          ) : (
            <div className="text-center py-6">
              <Award size={24} className="text-apple-gray-300 mx-auto mb-2" />
              <p className="text-sm text-apple-gray-400">No grading data yet</p>
              <p className="text-xs text-apple-gray-400 mt-1">Run daytrade digests to start tracking</p>
            </div>
          )}
        </div>
      </div>

      {/* Row 4: Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="card !p-4">
          <p className="text-xs text-apple-gray-400 uppercase tracking-wide">Cache Files</p>
          <p className="text-2xl font-semibold mt-1">{status.cache.file_count}</p>
          <p className="text-xs text-apple-gray-400">{(status.cache.total_size_bytes / 1024).toFixed(1)} KB</p>
        </div>
        <div className="card !p-4">
          <p className="text-xs text-apple-gray-400 uppercase tracking-wide">LLM Status</p>
          <p className="text-2xl font-semibold mt-1">{status.has_llm_key ? 'Ready' : 'No Keys'}</p>
          <p className="text-xs text-apple-gray-400">{status.has_llm_key ? 'Analysis available' : 'Facts-only mode'}</p>
        </div>
        <div className="card !p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-apple-gray-400 uppercase tracking-wide">API Health</p>
              <p className="text-2xl font-semibold mt-1">{configuredCount}/{apiEntries.length}</p>
              <p className="text-xs text-apple-gray-400">APIs connected</p>
            </div>
            <button
              onClick={() => setShowAllApis(!showAllApis)}
              className="text-xs text-apple-blue hover:underline"
            >
              {showAllApis ? 'Hide' : 'Show all'}
            </button>
          </div>
        </div>
      </div>

      {/* Row 5: API Health Grid (collapsible) */}
      {showAllApis && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 mb-6">
          {apiEntries.map(([key, info]) => (
            <div key={key} className="card !p-3 flex items-center gap-2">
              <StatusDot status={info.configured ? 'green' : 'gray'} size="sm" />
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-apple-gray-800 truncate">{info.name}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Row 6: Recent History */}
      {status.recent_history.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart3 size={16} className="text-apple-gray-400" />
              <h3 className="text-sm font-medium text-apple-gray-800">Recent Runs</h3>
            </div>
            <button
              onClick={() => navigate('/run')}
              className="text-xs text-apple-blue flex items-center gap-1 hover:underline"
            >
              Run & Preview <ChevronRight size={12} />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-apple-gray-400 uppercase tracking-wide">
                  <th className="pb-2 hidden sm:table-cell">Time</th>
                  <th className="pb-2">Type</th>
                  <th className="pb-2">Mode</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2 hidden sm:table-cell">Messages</th>
                </tr>
              </thead>
              <tbody>
                {status.recent_history.slice().reverse().map((entry, i) => (
                  <tr key={i} className="border-t border-apple-gray-100">
                    <td className="py-2 text-apple-gray-500 hidden sm:table-cell">
                      {new Date(entry.timestamp).toLocaleString()}
                    </td>
                    <td className="py-2 capitalize">{entry.type}</td>
                    <td className="py-2">{entry.mode}</td>
                    <td className="py-2">
                      <StatusDot status={entry.success ? 'green' : 'red'} />
                      <span className="ml-2">{entry.success ? 'Success' : 'Failed'}</span>
                    </td>
                    <td className="py-2 hidden sm:table-cell">{entry.message_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
