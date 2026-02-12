import { useState, useEffect } from 'react'
import {
  BarChart3, Sliders, GitBranch, Clock, Zap,
  Trophy, TrendingDown, Target, RefreshCw, RotateCcw, ChevronDown, CalendarDays,
  ArrowRight, AlertCircle, Check,
} from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import api from '../api/client'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ScoreCardDetail from '../components/common/ScoreCardDetail'
import ToastContainer from '../components/common/Toast'
import type {
  SnapshotMeta, PerformanceData, ScoringWeights,
  ConfigVersion, VersionDiff, GradingSummary, PickGrading,
  OptimizationResponse,
} from '../api/retrace-types'
import type { ScoreCardFull } from '../api/scorecard-types'

const tabs = [
  { id: 'performance', label: 'Performance', icon: BarChart3 },
  { id: 'scoring', label: 'Scoring', icon: Sliders },
  { id: 'optimize', label: 'Optimize', icon: Zap },
  { id: 'versions', label: 'Versions', icon: GitBranch },
  { id: 'audit', label: 'Audit Trail', icon: Clock },
] as const

type TabId = typeof tabs[number]['id']

export default function Retrace() {
  const [activeTab, setActiveTab] = useState<TabId>('performance')
  const { toasts, addToast, removeToast } = useToast()

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto pb-24 md:pb-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-apple-gray-800">Retrace</h1>
        <p className="text-sm text-apple-gray-400 mt-1">
          Review past picks, grade performance, tune scoring weights
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-apple-gray-100 rounded-xl p-1 mb-6">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex-1 justify-center ${
              activeTab === id
                ? 'bg-white text-apple-gray-800 shadow-sm'
                : 'text-apple-gray-500 hover:text-apple-gray-700'
            }`}
          >
            <Icon size={16} />
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {activeTab === 'performance' && <PerformanceTab addToast={addToast} />}
      {activeTab === 'scoring' && <ScoringTab addToast={addToast} />}
      {activeTab === 'optimize' && <OptimizeTab addToast={addToast} />}
      {activeTab === 'versions' && <VersionsTab addToast={addToast} />}
      {activeTab === 'audit' && <AuditTab />}

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}

// ── Performance Tab ─────────────────────────────────────────────

function PerformanceTab({ addToast }: { addToast: (msg: string, type: 'success' | 'error' | 'info') => void }) {
  const { data: perf, loading: perfLoading, refetch: refetchPerf } = useApi<PerformanceData>('/retrace/performance')
  const { data: snapshots, loading: snapsLoading, refetch: refetchSnaps } = useApi<SnapshotMeta[]>('/retrace/snapshots')
  const [grading, setGrading] = useState<string | null>(null)
  const [backfillDate, setBackfillDate] = useState('')
  const [backfilling, setBackfilling] = useState(false)

  const backfillAndGrade = async () => {
    if (!backfillDate) return
    setBackfilling(true)
    try {
      const res = await api.post(`/retrace/backfill-and-grade/${backfillDate}`)
      const msg = res.data.grading
        ? `Backfilled & graded ${backfillDate} — ${res.data.grading.win_rate}% WR`
        : `Backfilled ${backfillDate} (grading: ${res.data.grading_error || 'pending'})`
      addToast(msg, 'success')
      setBackfillDate('')
      refetchPerf()
      refetchSnaps()
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Backfill failed', 'error')
    } finally {
      setBackfilling(false)
    }
  }

  const gradeDate = async (date: string) => {
    setGrading(date)
    try {
      await api.post(`/retrace/grade/${date}`)
      addToast(`Graded ${date}`, 'success')
      refetchPerf()
      refetchSnaps()
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Grading failed', 'error')
    } finally {
      setGrading(null)
    }
  }

  const gradeAll = async () => {
    setGrading('all')
    try {
      const res = await api.post('/retrace/grade-all')
      addToast(`Graded ${res.data.graded} snapshots (${res.data.skipped} skipped)`, 'success')
      refetchPerf()
      refetchSnaps()
    } catch {
      addToast('Grading failed', 'error')
    } finally {
      setGrading(null)
    }
  }

  if (perfLoading || snapsLoading) return <LoadingSpinner />

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      {perf && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Win Rate" value={`${perf.win_rate}%`} sub={`${perf.wins}W / ${perf.losses}L`} color="green" />
          <StatCard label="Avg R:R" value={`${perf.avg_r_multiple}R`} sub={`${perf.total_picks} picks graded`} color="blue" />
          <StatCard label="Snapshots" value={`${perf.graded_snapshots}`} sub={`Last ${perf.days} days`} color="purple" />
          <StatCard label="Scratches" value={`${perf.scratches}`} sub={`${perf.ambiguous} ambiguous`} color="gray" />
        </div>
      )}

      {/* Timeline */}
      {perf && perf.timeline.length > 0 && (
        <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
          <h3 className="text-sm font-semibold text-apple-gray-700 mb-4">Daily Performance</h3>
          <div className="space-y-2">
            {perf.timeline.map(day => {
              const total = day.wins + day.losses + day.scratches
              const winPct = total > 0 ? (day.wins / total) * 100 : 0
              const lossPct = total > 0 ? (day.losses / total) * 100 : 0
              return (
                <div key={day.date} className="flex items-center gap-3">
                  <span className="text-xs text-apple-gray-500 w-20 shrink-0">{day.date}</span>
                  <div className="flex-1 h-5 bg-apple-gray-100 rounded-full overflow-hidden flex">
                    <div className="bg-green-400 h-full" style={{ width: `${winPct}%` }} />
                    <div className="bg-red-400 h-full" style={{ width: `${lossPct}%` }} />
                  </div>
                  <span className="text-xs font-medium text-apple-gray-600 w-16 text-right">
                    {day.win_rate}% WR
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Best & Worst picks */}
      {perf && (perf.best_picks.length > 0 || perf.worst_picks.length > 0) && (
        <div className="grid md:grid-cols-2 gap-4">
          {perf.best_picks.length > 0 && (
            <PicksTable title="Best Picks" icon={<Trophy size={16} className="text-green-500" />} picks={perf.best_picks} />
          )}
          {perf.worst_picks.length > 0 && (
            <PicksTable title="Worst Picks" icon={<TrendingDown size={16} className="text-red-500" />} picks={perf.worst_picks} />
          )}
        </div>
      )}

      {/* Win rate by signal */}
      {perf && Object.keys(perf.by_signal).length > 0 && (
        <BreakdownTable title="Win Rate by Signal" data={perf.by_signal} />
      )}

      {/* Win rate by trend */}
      {perf && Object.keys(perf.by_trend).length > 0 && (
        <BreakdownTable title="Win Rate by Trend" data={perf.by_trend} />
      )}

      {/* Backfill past date */}
      <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
        <h3 className="text-sm font-semibold text-apple-gray-700 mb-3 flex items-center gap-2">
          <CalendarDays size={16} className="text-yellow-500" />
          Backfill Past Date
        </h3>
        <p className="text-xs text-apple-gray-400 mb-3">
          Generate a retroactive snapshot for a date that didn't have one, then grade it against actual next-day prices.
        </p>
        <div className="flex gap-2">
          <input
            type="date"
            value={backfillDate}
            onChange={e => setBackfillDate(e.target.value)}
            max={new Date(Date.now() - 86400000).toISOString().split('T')[0]}
            className="flex-1 px-3 py-2 border border-apple-gray-200 rounded-lg text-sm"
          />
          <button
            onClick={backfillAndGrade}
            disabled={!backfillDate || backfilling}
            className="px-4 py-2 bg-yellow-500 text-white text-sm font-medium rounded-xl hover:bg-yellow-600 disabled:opacity-50 whitespace-nowrap"
          >
            {backfilling ? 'Backfilling...' : 'Backfill & Grade'}
          </button>
        </div>
      </div>

      {/* Snapshots list */}
      <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-apple-gray-700">Snapshots</h3>
          <button
            onClick={gradeAll}
            disabled={grading !== null}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-apple-blue text-white text-xs font-medium rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            <RefreshCw size={14} className={grading === 'all' ? 'animate-spin' : ''} />
            Grade All Ungraded
          </button>
        </div>
        {!snapshots || snapshots.length === 0 ? (
          <p className="text-sm text-apple-gray-400 text-center py-8">
            No snapshots yet. Run a digest to create one.
          </p>
        ) : (
          <div className="space-y-2">
            {snapshots.map(snap => {
              const digestType = snap.digest_type || 'daytrade'
              const isDaytrade = digestType === 'daytrade'
              const typeBadgeColors: Record<string, string> = {
                daytrade: 'bg-blue-100 text-blue-700',
                morning: 'bg-amber-100 text-amber-700',
                afternoon: 'bg-orange-100 text-orange-700',
                weekly: 'bg-purple-100 text-purple-700',
              }
              return (
                <div key={snap.date} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-apple-gray-50">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-apple-gray-800">{snap.date}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${typeBadgeColors[digestType] || 'bg-gray-100 text-gray-700'}`}>
                      {digestType}
                    </span>
                    {isDaytrade && (
                      <span className="text-xs text-apple-gray-400">{snap.pick_count} picks</span>
                    )}
                    {snap.backfilled && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded-full font-semibold">Backfilled</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {isDaytrade && (
                      snap.has_grading ? (
                        <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full font-medium">Graded</span>
                      ) : (
                        <button
                          onClick={() => gradeDate(snap.date)}
                          disabled={grading !== null}
                          className="text-xs px-2 py-0.5 bg-apple-blue/10 text-apple-blue rounded-full font-medium hover:bg-apple-blue/20 disabled:opacity-50"
                        >
                          {grading === snap.date ? 'Grading...' : 'Grade'}
                        </button>
                      )
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  const colors: Record<string, string> = {
    green: 'text-green-600',
    blue: 'text-blue-600',
    purple: 'text-purple-600',
    gray: 'text-apple-gray-600',
  }
  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-4">
      <p className="text-xs text-apple-gray-400 font-medium">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${colors[color] || colors.gray}`}>{value}</p>
      <p className="text-xs text-apple-gray-400 mt-0.5">{sub}</p>
    </div>
  )
}

function PicksTable({ title, icon, picks }: { title: string; icon: React.ReactNode; picks: PickGrading[] }) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const [cardData, setCardData] = useState<ScoreCardFull | null>(null)
  const [cardLoading, setCardLoading] = useState(false)

  const toggleRow = async (symbol: string) => {
    if (expanded === symbol) {
      setExpanded(null)
      setCardData(null)
      return
    }
    setExpanded(symbol)
    setCardData(null)
    setCardLoading(true)
    try {
      const res = await api.get<ScoreCardFull>(`/scorecard/${symbol}`)
      setCardData(res.data)
    } catch {
      setCardData(null)
    } finally {
      setCardLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <h3 className="text-sm font-semibold text-apple-gray-700 mb-3 flex items-center gap-2">{icon}{title}</h3>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-apple-gray-400">
            <th className="text-left pb-2">Symbol</th>
            <th className="text-right pb-2">Entry</th>
            <th className="text-right pb-2">Return</th>
            <th className="text-right pb-2">R</th>
          </tr>
        </thead>
        <tbody>
          {picks.map((p, i) => (
            <>
              <tr
                key={i}
                onClick={() => toggleRow(p.symbol)}
                className="border-t border-apple-gray-100 cursor-pointer hover:bg-apple-gray-50 transition-colors"
              >
                <td className="py-1.5 font-medium text-apple-blue">{p.symbol}</td>
                <td className="py-1.5 text-right text-apple-gray-600">${p.entry?.toFixed(2)}</td>
                <td className={`py-1.5 text-right font-medium ${(p.actual_return_pct ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {p.actual_return_pct !== undefined ? `${p.actual_return_pct > 0 ? '+' : ''}${p.actual_return_pct}%` : '-'}
                </td>
                <td className={`py-1.5 text-right font-medium ${(p.r_multiple ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {p.r_multiple !== undefined ? `${p.r_multiple > 0 ? '+' : ''}${p.r_multiple}R` : '-'}
                </td>
              </tr>
              {expanded === p.symbol && (
                <tr key={`${i}-detail`}>
                  <td colSpan={4} className="py-3 px-1">
                    {cardLoading && <LoadingSpinner />}
                    {cardData && <ScoreCardDetail card={cardData} />}
                    {!cardLoading && !cardData && (
                      <p className="text-xs text-apple-gray-400 text-center py-2">
                        Could not load score card for {p.symbol}
                      </p>
                    )}
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function BreakdownTable({ title, data }: { title: string; data: Record<string, { wins: number; losses: number; scratches: number; total: number; win_rate: number }> }) {
  const sorted = Object.entries(data).sort((a, b) => b[1].total - a[1].total)
  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <h3 className="text-sm font-semibold text-apple-gray-700 mb-3">{title}</h3>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-apple-gray-400">
            <th className="text-left pb-2">Type</th>
            <th className="text-right pb-2">Total</th>
            <th className="text-right pb-2">W</th>
            <th className="text-right pb-2">L</th>
            <th className="text-right pb-2">Win Rate</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(([key, stats]) => (
            <tr key={key} className="border-t border-apple-gray-100">
              <td className="py-1.5 font-medium text-apple-gray-800">{key}</td>
              <td className="py-1.5 text-right text-apple-gray-600">{stats.total}</td>
              <td className="py-1.5 text-right text-green-600">{stats.wins}</td>
              <td className="py-1.5 text-right text-red-600">{stats.losses}</td>
              <td className="py-1.5 text-right font-medium text-apple-gray-800">{stats.win_rate}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Scoring Tab ─────────────────────────────────────────────────

function ScoringTab({ addToast }: { addToast: (msg: string, type: 'success' | 'error' | 'info') => void }) {
  const { data, loading, refetch } = useApi<ScoringWeights>('/retrace/scoring')
  const [weights, setWeights] = useState<Record<string, number>>({})
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (data) setWeights({ ...data.weights })
  }, [data])

  const total = Object.values(weights).reduce((a, b) => a + b, 0)
  const isValid = Math.abs(total - 1.0) < 0.001

  const handleSlider = (key: string, val: number) => {
    setWeights(prev => ({ ...prev, [key]: Math.round(val * 100) / 100 }))
  }

  const save = async () => {
    if (!isValid) return
    setSaving(true)
    try {
      await api.put('/retrace/scoring', { weights, description })
      addToast('Scoring weights saved', 'success')
      setDescription('')
      refetch()
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  const reset = async () => {
    try {
      await api.post('/retrace/scoring/reset')
      addToast('Weights reset to defaults', 'success')
      refetch()
    } catch {
      addToast('Reset failed', 'error')
    }
  }

  if (loading) return <LoadingSpinner />

  const labels: Record<string, string> = {
    rsi: 'RSI Momentum',
    trend: 'Trend Alignment',
    pivot: 'Pivot Proximity',
    atr: 'ATR Volatility',
    volume: 'Volume',
    gap: 'Gap Analysis',
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-sm font-semibold text-apple-gray-700">Scoring Weights</h3>
          <div className={`text-sm font-bold px-3 py-1 rounded-full ${
            isValid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {(total * 100).toFixed(0)}%
          </div>
        </div>

        <div className="space-y-5">
          {Object.entries(weights).map(([key, val]) => (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <label className="text-sm font-medium text-apple-gray-700">{labels[key] || key}</label>
                <span className="text-sm font-mono text-apple-gray-500">{(val * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={0.5}
                step={0.01}
                value={val}
                onChange={e => handleSlider(key, parseFloat(e.target.value))}
                className="w-full h-2 bg-apple-gray-200 rounded-lg appearance-none cursor-pointer accent-apple-blue"
              />
            </div>
          ))}
        </div>

        <div className="mt-5 pt-4 border-t border-apple-gray-100">
          <label className="text-sm font-medium text-apple-gray-700 block mb-1">Change description</label>
          <input
            type="text"
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="e.g. Increased RSI weight for momentum plays"
            className="w-full px-3 py-2 border border-apple-gray-200 rounded-lg text-sm"
          />
        </div>

        <div className="flex gap-3 mt-4">
          <button
            onClick={save}
            disabled={!isValid || saving}
            className="flex-1 px-4 py-2 bg-apple-blue text-white text-sm font-medium rounded-xl hover:bg-blue-600 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Weights'}
          </button>
          <button
            onClick={reset}
            className="px-4 py-2 border border-apple-gray-200 text-apple-gray-600 text-sm font-medium rounded-xl hover:bg-apple-gray-50"
          >
            <RotateCcw size={14} className="inline mr-1" />
            Reset
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Optimize Tab ────────────────────────────────────────────────

const indicatorLabels: Record<string, string> = {
  rsi: 'RSI Momentum',
  trend: 'Trend Alignment',
  pivot: 'Pivot Proximity',
  atr: 'ATR Volatility',
  volume: 'Volume',
  gap: 'Gap Analysis',
}

function OptimizeTab({ addToast }: { addToast: (msg: string, type: 'success' | 'error' | 'info') => void }) {
  const [result, setResult] = useState<OptimizationResponse | null>(null)
  const [running, setRunning] = useState(false)
  const [applying, setApplying] = useState(false)
  const [confirmApply, setConfirmApply] = useState(false)

  const runOptimizer = async () => {
    setRunning(true)
    setResult(null)
    setConfirmApply(false)
    try {
      const res = await api.post<OptimizationResponse>('/retrace/optimize')
      setResult(res.data)
      addToast('Optimization complete', 'success')
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Optimization failed — not enough graded data?', 'error')
    } finally {
      setRunning(false)
    }
  }

  const applyWeights = async () => {
    if (!result || !confirmApply) {
      setConfirmApply(true)
      return
    }
    setApplying(true)
    try {
      const opt = result.optimization
      const changes = Object.entries(opt.weight_changes)
        .filter(([, v]) => Math.abs(v.change) >= 0.01)
        .map(([k, v]) => `${k} ${v.change > 0 ? '+' : ''}${(v.change * 100).toFixed(0)}%`)
        .join(', ')
      await api.post('/retrace/optimize/apply', {
        weights: opt.suggested_weights,
        description: `Auto-tuned (${opt.pick_count} picks): ${changes}`,
      })
      addToast('Optimized weights applied and versioned', 'success')
      setConfirmApply(false)
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Apply failed', 'error')
    } finally {
      setApplying(false)
    }
  }

  const opt = result?.optimization

  return (
    <div className="space-y-6">
      {/* Run button card */}
      <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
        <div className="flex items-start gap-4">
          <div className="p-2.5 bg-amber-100 rounded-xl shrink-0">
            <Zap size={20} className="text-amber-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-apple-gray-800">Auto-Tune Scoring Weights</h3>
            <p className="text-xs text-apple-gray-400 mt-1">
              Analyzes your graded pick history to find weights that maximize the correlation between
              composite scores and actual R-multiples. Requires at least 30 graded picks.
            </p>
          </div>
          <button
            onClick={runOptimizer}
            disabled={running}
            className="px-5 py-2.5 bg-amber-500 text-white text-sm font-medium rounded-xl hover:bg-amber-600 disabled:opacity-50 shrink-0 flex items-center gap-2"
          >
            {running ? (
              <>
                <RefreshCw size={14} className="animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Zap size={14} />
                Run Optimization
              </>
            )}
          </button>
        </div>
      </div>

      {/* Data summary */}
      {result && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-white rounded-xl border border-apple-gray-200 p-3 text-center">
            <p className="text-2xl font-bold text-apple-gray-800">{result.data_summary.total_picks}</p>
            <p className="text-xs text-apple-gray-400">Total Picks</p>
          </div>
          <div className="bg-white rounded-xl border border-apple-gray-200 p-3 text-center">
            <p className="text-2xl font-bold text-apple-gray-800">{result.data_summary.snapshots_used}</p>
            <p className="text-xs text-apple-gray-400">Snapshots</p>
          </div>
          <div className="bg-white rounded-xl border border-apple-gray-200 p-3 text-center">
            <p className="text-2xl font-bold text-green-600">{result.data_summary.outcomes.win || 0}W</p>
            <p className="text-xs text-apple-gray-400">
              / {result.data_summary.outcomes.loss || 0}L / {result.data_summary.outcomes.scratch || 0}S
            </p>
          </div>
          <div className="bg-white rounded-xl border border-apple-gray-200 p-3 text-center">
            <p className={`text-2xl font-bold ${opt?.optimization_converged ? 'text-green-600' : 'text-amber-500'}`}>
              {opt?.optimization_converged ? 'Yes' : 'No'}
            </p>
            <p className="text-xs text-apple-gray-400">Converged</p>
          </div>
        </div>
      )}

      {/* Weight comparison */}
      {opt && (
        <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
          <h3 className="text-sm font-semibold text-apple-gray-700 mb-4">Weight Comparison</h3>
          <div className="space-y-4">
            {Object.entries(opt.weight_changes).map(([key, wc]) => {
              const changeColor = wc.change > 0.005 ? 'text-green-600' : wc.change < -0.005 ? 'text-red-500' : 'text-apple-gray-400'
              const changeSign = wc.change > 0 ? '+' : ''
              return (
                <div key={key}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-apple-gray-700">{indicatorLabels[key] || key}</span>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-apple-gray-400 font-mono">{(wc.current * 100).toFixed(0)}%</span>
                      <ArrowRight size={12} className="text-apple-gray-300" />
                      <span className="text-apple-gray-800 font-mono font-semibold">{(wc.suggested * 100).toFixed(0)}%</span>
                      <span className={`font-mono font-semibold ${changeColor}`}>
                        {changeSign}{(wc.change * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-1 h-2">
                    <div className="flex-1 bg-apple-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-apple-gray-300 rounded-full" style={{ width: `${wc.current * 100 * 2}%` }} />
                    </div>
                    <div className="flex-1 bg-amber-50 rounded-full overflow-hidden">
                      <div className="h-full bg-amber-400 rounded-full" style={{ width: `${wc.suggested * 100 * 2}%` }} />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Metrics improvement */}
      {opt && (
        <div className="grid md:grid-cols-3 gap-4">
          <MetricCard
            label="Spearman Correlation"
            current={opt.metrics.current.spearman_correlation}
            suggested={opt.metrics.suggested.spearman_correlation}
            format={v => v.toFixed(3)}
            higherBetter
          />
          <MetricCard
            label="Mean R (Top-K)"
            current={opt.metrics.current.mean_r_top_k}
            suggested={opt.metrics.suggested.mean_r_top_k}
            format={v => `${v > 0 ? '+' : ''}${v.toFixed(2)}R`}
            higherBetter
          />
          <MetricCard
            label="Profit Factor"
            current={opt.metrics.current.profit_factor}
            suggested={opt.metrics.suggested.profit_factor}
            format={v => v.toFixed(2)}
            higherBetter
          />
        </div>
      )}

      {/* Indicator effectiveness */}
      {result && result.indicator_effectiveness.length > 0 && (
        <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
          <h3 className="text-sm font-semibold text-apple-gray-700 mb-4">Indicator Effectiveness</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-apple-gray-400 border-b border-apple-gray-100">
                  <th className="text-left pb-2 pr-3">#</th>
                  <th className="text-left pb-2 pr-3">Indicator</th>
                  <th className="text-right pb-2 pr-3">Corr w/ R</th>
                  <th className="text-right pb-2 pr-3">p-value</th>
                  <th className="text-right pb-2 pr-3">Avg Win</th>
                  <th className="text-right pb-2 pr-3">Avg Loss</th>
                  <th className="text-right pb-2 pr-3">Spread</th>
                  <th className="text-right pb-2">Pred WR</th>
                </tr>
              </thead>
              <tbody>
                {result.indicator_effectiveness.map(ind => {
                  const corrColor = ind.correlation_with_r > 0.1 ? 'text-green-600' : ind.correlation_with_r < -0.1 ? 'text-red-500' : 'text-apple-gray-500'
                  const sigMarker = ind.p_value < 0.05 ? '*' : ''
                  return (
                    <tr key={ind.name} className="border-b border-apple-gray-50">
                      <td className="py-2 pr-3 text-apple-gray-400">{ind.effectiveness_rank}</td>
                      <td className="py-2 pr-3 font-medium text-apple-gray-800">{indicatorLabels[ind.name] || ind.name}</td>
                      <td className={`py-2 pr-3 text-right font-mono font-semibold ${corrColor}`}>
                        {ind.correlation_with_r.toFixed(3)}{sigMarker}
                      </td>
                      <td className="py-2 pr-3 text-right font-mono text-apple-gray-400">{ind.p_value.toFixed(3)}</td>
                      <td className="py-2 pr-3 text-right text-green-600">{ind.avg_score_for_wins.toFixed(0)}</td>
                      <td className="py-2 pr-3 text-right text-red-500">{ind.avg_score_for_losses.toFixed(0)}</td>
                      <td className="py-2 pr-3 text-right text-apple-gray-500">{ind.score_spread.toFixed(1)}</td>
                      <td className="py-2 text-right font-medium text-apple-gray-700">{ind.predictive_win_rate}%</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Caveats */}
      {result && result.caveats.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle size={14} className="text-amber-600" />
            <span className="text-xs font-semibold text-amber-700">Caveats</span>
          </div>
          <ul className="space-y-1">
            {result.caveats.map((c, i) => (
              <li key={i} className="text-xs text-amber-700">{c}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Apply button */}
      {opt && (
        <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-apple-gray-700">Apply Suggested Weights</h3>
              <p className="text-xs text-apple-gray-400 mt-0.5">
                Saves the optimized weights and creates a version snapshot.
              </p>
            </div>
            <button
              onClick={applyWeights}
              disabled={applying}
              className={`px-5 py-2.5 text-sm font-medium rounded-xl flex items-center gap-2 transition-colors ${
                confirmApply
                  ? 'bg-green-500 text-white hover:bg-green-600'
                  : 'bg-apple-blue text-white hover:bg-blue-600'
              } disabled:opacity-50`}
            >
              {applying ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  Applying...
                </>
              ) : confirmApply ? (
                <>
                  <Check size={14} />
                  Confirm Apply
                </>
              ) : (
                'Apply Suggested Weights'
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, current, suggested, format, higherBetter }: {
  label: string
  current: number
  suggested: number
  format: (v: number) => string
  higherBetter: boolean
}) {
  const improved = higherBetter ? suggested > current : suggested < current
  const diff = suggested - current
  const pctChange = current !== 0 ? ((diff / Math.abs(current)) * 100) : 0

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-4">
      <p className="text-xs text-apple-gray-400 font-medium mb-3">{label}</p>
      <div className="flex items-end justify-between">
        <div>
          <p className="text-xs text-apple-gray-400">Current</p>
          <p className="text-lg font-bold text-apple-gray-600">{format(current)}</p>
        </div>
        <ArrowRight size={14} className="text-apple-gray-300 mb-2" />
        <div className="text-right">
          <p className="text-xs text-apple-gray-400">Suggested</p>
          <p className={`text-lg font-bold ${improved ? 'text-green-600' : 'text-apple-gray-800'}`}>
            {format(suggested)}
          </p>
        </div>
      </div>
      {Math.abs(pctChange) > 0.5 && (
        <p className={`text-xs mt-2 font-medium ${improved ? 'text-green-600' : 'text-red-500'}`}>
          {pctChange > 0 ? '+' : ''}{pctChange.toFixed(0)}% {improved ? 'improvement' : 'change'}
        </p>
      )}
    </div>
  )
}

// ── Versions Tab ────────────────────────────────────────────────

function VersionsTab({ addToast }: { addToast: (msg: string, type: 'success' | 'error' | 'info') => void }) {
  const [configType, setConfigType] = useState<'scoring' | 'prompts'>('scoring')
  const { data: versions, loading, refetch } = useApi<ConfigVersion[]>(`/retrace/versions/${configType}`, [configType])
  const [selectedA, setSelectedA] = useState<string | null>(null)
  const [selectedB, setSelectedB] = useState<string | null>(null)
  const [diff, setDiff] = useState<VersionDiff | null>(null)
  const [diffLoading, setDiffLoading] = useState(false)
  const [expandedVersion, setExpandedVersion] = useState<string | null>(null)
  const [versionContent, setVersionContent] = useState<Record<string, unknown> | null>(null)

  const loadDiff = async () => {
    if (!selectedA || !selectedB) return
    setDiffLoading(true)
    try {
      const res = await api.get(`/retrace/versions/${configType}/diff`, { params: { a: selectedA, b: selectedB } })
      setDiff(res.data)
    } catch {
      addToast('Failed to load diff', 'error')
    } finally {
      setDiffLoading(false)
    }
  }

  const viewVersion = async (versionId: string) => {
    if (expandedVersion === versionId) {
      setExpandedVersion(null)
      setVersionContent(null)
      return
    }
    try {
      const res = await api.get(`/retrace/versions/${configType}/${versionId}`)
      setExpandedVersion(versionId)
      setVersionContent(res.data.content)
    } catch {
      addToast('Failed to load version', 'error')
    }
  }

  const doRollback = async (versionId: string) => {
    try {
      await api.post('/retrace/versions/rollback', { config_name: configType, version_id: versionId })
      addToast(`Rolled back ${configType} to ${versionId}`, 'success')
      refetch()
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Rollback failed', 'error')
    }
  }

  useEffect(() => {
    setSelectedA(null)
    setSelectedB(null)
    setDiff(null)
    setExpandedVersion(null)
    setVersionContent(null)
  }, [configType])

  return (
    <div className="space-y-6">
      {/* Config type selector */}
      <div className="flex gap-2">
        {(['scoring', 'prompts'] as const).map(t => (
          <button
            key={t}
            onClick={() => setConfigType(t)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              configType === t ? 'bg-apple-blue text-white' : 'bg-apple-gray-100 text-apple-gray-600 hover:bg-apple-gray-200'
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {loading ? <LoadingSpinner /> : (
        <>
          {/* Version list */}
          <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
            <h3 className="text-sm font-semibold text-apple-gray-700 mb-4">Version History</h3>
            {!versions || versions.length === 0 ? (
              <p className="text-sm text-apple-gray-400 text-center py-6">No versions recorded yet.</p>
            ) : (
              <div className="space-y-2">
                {versions.map((v, i) => (
                  <div key={v.version_id} className="border border-apple-gray-100 rounded-xl">
                    <div className="flex items-center gap-3 p-3">
                      {/* Diff selection checkboxes */}
                      <div className="flex gap-1">
                        <input
                          type="radio"
                          name="diffA"
                          checked={selectedA === v.version_id}
                          onChange={() => setSelectedA(v.version_id)}
                          className="accent-apple-blue"
                          title="Select as version A"
                        />
                        <input
                          type="radio"
                          name="diffB"
                          checked={selectedB === v.version_id}
                          onChange={() => setSelectedB(v.version_id)}
                          className="accent-red-500"
                          title="Select as version B"
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-apple-gray-800 truncate">{v.description}</p>
                        <p className="text-xs text-apple-gray-400">{v.version_id}</p>
                      </div>
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => viewVersion(v.version_id)}
                          className="text-xs px-2 py-1 text-apple-blue hover:bg-apple-blue/10 rounded-lg"
                        >
                          {expandedVersion === v.version_id ? 'Hide' : 'View'}
                        </button>
                        {i > 0 && (
                          <button
                            onClick={() => doRollback(v.version_id)}
                            className="text-xs px-2 py-1 text-orange-600 hover:bg-orange-50 rounded-lg"
                          >
                            Rollback
                          </button>
                        )}
                      </div>
                    </div>
                    {expandedVersion === v.version_id && versionContent && (
                      <div className="border-t border-apple-gray-100 p-3">
                        <pre className="text-xs text-apple-gray-600 bg-apple-gray-50 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                          {JSON.stringify(versionContent, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Diff section */}
          {selectedA && selectedB && selectedA !== selectedB && (
            <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-apple-gray-700">
                  Diff: <span className="font-mono text-apple-blue">{selectedA}</span> vs <span className="font-mono text-red-500">{selectedB}</span>
                </h3>
                <button
                  onClick={loadDiff}
                  disabled={diffLoading}
                  className="px-3 py-1.5 bg-apple-blue text-white text-xs font-medium rounded-lg hover:bg-blue-600 disabled:opacity-50"
                >
                  {diffLoading ? 'Loading...' : 'Compare'}
                </button>
              </div>
              {diff && (
                <div className="space-y-1">
                  {diff.changes.length === 0 ? (
                    <p className="text-sm text-apple-gray-400 text-center py-4">No differences found.</p>
                  ) : (
                    diff.changes.map((c, i) => (
                      <div key={i} className="flex gap-3 text-xs py-1.5 border-b border-apple-gray-50">
                        <span className="font-mono font-medium text-apple-gray-700 w-40 shrink-0">{c.key}</span>
                        <span className="text-red-500 flex-1"><span className="font-mono bg-red-50 px-1 rounded">{String(c.old ?? '—')}</span></span>
                        <span className="text-apple-gray-300">→</span>
                        <span className="text-green-600 flex-1"><span className="font-mono bg-green-50 px-1 rounded">{String(c.new ?? '—')}</span></span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ── Audit Trail Tab ─────────────────────────────────────────────

function AuditTab() {
  const { data: scoringVersions } = useApi<ConfigVersion[]>('/retrace/versions/scoring')
  const { data: promptsVersions } = useApi<ConfigVersion[]>('/retrace/versions/prompts')
  const { data: snapshots } = useApi<SnapshotMeta[]>('/retrace/snapshots')

  // Merge all events into a single timeline
  const events: { timestamp: string; type: 'scoring' | 'prompts' | 'digest'; description: string; id: string }[] = []

  scoringVersions?.forEach(v => {
    events.push({
      timestamp: v.timestamp,
      type: 'scoring',
      description: v.description,
      id: v.version_id,
    })
  })

  promptsVersions?.forEach(v => {
    events.push({
      timestamp: v.timestamp,
      type: 'prompts',
      description: v.description,
      id: v.version_id,
    })
  })

  snapshots?.forEach(s => {
    const dtype = s.digest_type || 'daytrade'
    const pickInfo = dtype === 'daytrade' ? ` — ${s.pick_count} picks` : ''
    events.push({
      timestamp: s.timestamp,
      type: 'digest',
      description: `${dtype.charAt(0).toUpperCase() + dtype.slice(1)} digest${pickInfo}${s.has_grading ? ' (graded)' : ''}`,
      id: s.date,
    })
  })

  events.sort((a, b) => b.timestamp.localeCompare(a.timestamp))

  const typeStyles: Record<string, { bg: string; text: string; label: string }> = {
    scoring: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Scoring' },
    prompts: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Prompts' },
    digest: { bg: 'bg-green-100', text: 'text-green-700', label: 'Digest' },
  }

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <h3 className="text-sm font-semibold text-apple-gray-700 mb-4">All Changes</h3>
      {events.length === 0 ? (
        <p className="text-sm text-apple-gray-400 text-center py-8">No events recorded yet.</p>
      ) : (
        <div className="space-y-3">
          {events.map((ev, i) => {
            const style = typeStyles[ev.type]
            return (
              <div key={`${ev.type}-${ev.id}-${i}`} className="flex items-start gap-3 py-2">
                <div className="w-2 h-2 rounded-full bg-apple-gray-300 mt-1.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${style.bg} ${style.text}`}>
                      {style.label}
                    </span>
                    <span className="text-xs text-apple-gray-400">
                      {new Date(ev.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm text-apple-gray-700 truncate">{ev.description}</p>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
