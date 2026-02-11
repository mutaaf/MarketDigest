import { useState, useEffect } from 'react'
import {
  BarChart3, Sliders, GitBranch, Clock,
  Trophy, TrendingDown, Target, RefreshCw, RotateCcw, ChevronDown,
} from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import api from '../api/client'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ToastContainer from '../components/common/Toast'
import type {
  SnapshotMeta, PerformanceData, ScoringWeights,
  ConfigVersion, VersionDiff, GradingSummary, PickGrading,
} from '../api/retrace-types'

const tabs = [
  { id: 'performance', label: 'Performance', icon: BarChart3 },
  { id: 'scoring', label: 'Scoring', icon: Sliders },
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
    } catch (err: any) {
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
            No snapshots yet. Run a daytrade digest to create one.
          </p>
        ) : (
          <div className="space-y-2">
            {snapshots.map(snap => (
              <div key={snap.date} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-apple-gray-50">
                <div>
                  <span className="text-sm font-medium text-apple-gray-800">{snap.date}</span>
                  <span className="text-xs text-apple-gray-400 ml-2">{snap.pick_count} picks</span>
                </div>
                <div className="flex items-center gap-2">
                  {snap.has_grading ? (
                    <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full font-medium">Graded</span>
                  ) : (
                    <button
                      onClick={() => gradeDate(snap.date)}
                      disabled={grading !== null}
                      className="text-xs px-2 py-0.5 bg-apple-blue/10 text-apple-blue rounded-full font-medium hover:bg-apple-blue/20 disabled:opacity-50"
                    >
                      {grading === snap.date ? 'Grading...' : 'Grade'}
                    </button>
                  )}
                </div>
              </div>
            ))}
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
            <tr key={i} className="border-t border-apple-gray-100">
              <td className="py-1.5 font-medium text-apple-gray-800">{p.symbol}</td>
              <td className="py-1.5 text-right text-apple-gray-600">${p.entry?.toFixed(2)}</td>
              <td className={`py-1.5 text-right font-medium ${(p.actual_return_pct ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {p.actual_return_pct !== undefined ? `${p.actual_return_pct > 0 ? '+' : ''}${p.actual_return_pct}%` : '-'}
              </td>
              <td className={`py-1.5 text-right font-medium ${(p.r_multiple ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {p.r_multiple !== undefined ? `${p.r_multiple > 0 ? '+' : ''}${p.r_multiple}R` : '-'}
              </td>
            </tr>
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
    events.push({
      timestamp: s.timestamp,
      type: 'digest',
      description: `Daytrade digest — ${s.pick_count} picks${s.has_grading ? ' (graded)' : ''}`,
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
