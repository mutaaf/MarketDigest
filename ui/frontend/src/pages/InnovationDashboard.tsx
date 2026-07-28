import { useState, useEffect, useCallback } from 'react'
import api from '../api/client'

export default function InnovationDashboard() {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const refresh = useCallback(async () => {
    try {
      const res = await api.get('/innovation/status')
      setStatus(res.data)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const toggleAgent = async () => {
    setLoading(true)
    try {
      if (status?.running) {
        await api.post('/innovation/stop')
        setMessage('Innovation Agent stopped')
      } else {
        await api.post('/innovation/start')
        setMessage('Innovation Agent started — will run daily learning cycles')
      }
      await refresh()
    } catch (e: any) {
      setMessage(e.response?.data?.detail || 'Error')
    } finally {
      setLoading(false)
    }
  }

  const setMode = async (mode: string) => {
    try {
      await api.post('/innovation/mode', { mode })
      setMessage(`Mode set to ${mode}`)
      await refresh()
    } catch (e: any) {
      setMessage(e.response?.data?.detail || 'Error')
    }
  }

  const runCycle = async (type: 'daily' | 'weekly') => {
    setLoading(true)
    setMessage(`Running ${type} cycle...`)
    try {
      const res = await api.post(`/innovation/${type}-cycle`)
      setMessage(`${type} cycle complete — ${res.data.changes_applied || 0} changes applied`)
      await refresh()
    } catch (e: any) {
      setMessage(e.response?.data?.detail || 'Cycle failed')
    } finally {
      setLoading(false)
    }
  }

  if (!status) return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-500">Loading...</div>

  const strategies = status.strategies || {}
  const sortedStrats = Object.entries(strategies).sort((a: any, b: any) => (b[1].total_pnl || 0) - (a[1].total_pnl || 0))
  const performers = status.performers || {}
  const changes = status.recent_changes || []
  const regime = status.regime || {}

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            Innovation Agent
            <span className={`w-3 h-3 rounded-full ${status.running ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
          </h1>
          <p className="text-gray-500 text-sm">Self-improving strategy optimizer — learns, tunes, adapts</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Mode selector */}
          <div className="flex gap-1 bg-gray-800 rounded-lg p-0.5">
            {['auto-tune', 'suggest', 'off'].map(m => (
              <button key={m} onClick={() => setMode(m)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  status.mode === m ? 'bg-blue-600 text-white' : 'text-gray-500 hover:text-gray-300'
                }`}>
                {m}
              </button>
            ))}
          </div>
          <button onClick={toggleAgent} disabled={loading}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition-colors ${
              status.running ? 'bg-red-600/20 text-red-400 hover:bg-red-600/40' : 'bg-green-600 text-white hover:bg-green-500'
            }`}>
            {loading ? '...' : status.running ? 'Stop Agent' : 'Start Agent'}
          </button>
        </div>
      </div>

      {message && <div className="mb-4 px-4 py-2 rounded-lg bg-gray-800 text-sm text-gray-300 border border-gray-700">{message}</div>}

      {/* Quick Stats */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <div className="text-[10px] text-gray-500 uppercase">Mode</div>
          <div className={`text-lg font-bold ${status.mode === 'auto-tune' ? 'text-green-400' : status.mode === 'suggest' ? 'text-amber-400' : 'text-gray-500'}`}>
            {status.mode || 'off'}
          </div>
        </div>
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <div className="text-[10px] text-gray-500 uppercase">Cycles Run</div>
          <div className="text-lg font-bold font-mono">{status.cycles_run || 0}</div>
        </div>
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <div className="text-[10px] text-gray-500 uppercase">30d Trades</div>
          <div className="text-lg font-bold font-mono">{status.performance?.total_trades_30d || 0}</div>
        </div>
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <div className="text-[10px] text-gray-500 uppercase">30d P&L</div>
          <div className={`text-lg font-bold font-mono ${(status.performance?.total_pnl_30d || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            ${(status.performance?.total_pnl_30d || 0).toFixed(2)}
          </div>
        </div>
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <div className="text-[10px] text-gray-500 uppercase">30d Win Rate</div>
          <div className={`text-lg font-bold font-mono ${(status.performance?.win_rate_30d || 0) >= 50 ? 'text-green-400' : 'text-red-400'}`}>
            {(status.performance?.win_rate_30d || 0).toFixed(0)}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Strategy Performance */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <div className="px-4 py-3 bg-gray-800 text-sm font-semibold text-gray-400 flex justify-between items-center">
            Strategy Performance (30d)
            <button onClick={() => runCycle('daily')} disabled={loading}
              className="text-xs px-3 py-1 rounded bg-blue-600/20 text-blue-400 hover:bg-blue-600/40">
              {loading ? 'Running...' : 'Run Daily Cycle'}
            </button>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase">
                <th className="px-4 py-2 text-left">Strategy</th>
                <th className="px-4 py-2 text-right">Trades</th>
                <th className="px-4 py-2 text-right">WR</th>
                <th className="px-4 py-2 text-right">Avg R</th>
                <th className="px-4 py-2 text-right">P&L</th>
              </tr>
            </thead>
            <tbody>
              {sortedStrats.map(([name, m]: any) => (
                <tr key={name} className="border-t border-gray-800">
                  <td className="px-4 py-2 font-medium">{name}</td>
                  <td className="px-4 py-2 text-right font-mono">{m.total_trades}</td>
                  <td className={`px-4 py-2 text-right font-mono ${m.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>{m.win_rate}%</td>
                  <td className={`px-4 py-2 text-right font-mono ${m.avg_r >= 0 ? 'text-green-400' : 'text-red-400'}`}>{m.avg_r}</td>
                  <td className={`px-4 py-2 text-right font-mono font-bold ${m.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>${m.total_pnl?.toFixed(2)}</td>
                </tr>
              ))}
              {sortedStrats.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-600">No trade data yet. Run autopilot to generate trades.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Recent Changes + Regime */}
        <div className="space-y-6">
          {/* Regime */}
          <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Market Regime</h3>
            {regime.current?.distribution ? (
              <div className="space-y-2">
                {Object.entries(regime.current.distribution).map(([r, count]: any) => (
                  <div key={r} className="flex items-center gap-2">
                    <span className="w-24 text-xs text-gray-500">{r.replace('_', ' ')}</span>
                    <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(count / (regime.current.total_instruments || 1)) * 100}%` }} />
                    </div>
                    <span className="text-xs text-gray-400 font-mono w-8 text-right">{count}</span>
                  </div>
                ))}
                {regime.shift && (
                  <div className="mt-2 text-xs text-amber-400 bg-amber-500/10 rounded px-2 py-1">{regime.shift.message}</div>
                )}
                {regime.overrides?.note && (
                  <div className="text-xs text-blue-400 mt-1">{regime.overrides.note}</div>
                )}
              </div>
            ) : (
              <div className="text-gray-600 text-sm">No regime data yet. Run a scan first.</div>
            )}
          </div>

          {/* Recent Changes */}
          <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Recent Parameter Changes</h3>
            {changes.length > 0 ? (
              <div className="space-y-2">
                {changes.slice(0, 8).map((c: any, i: number) => (
                  <div key={i} className="text-xs bg-gray-800 rounded p-2">
                    <div className="flex justify-between">
                      <span className="text-cyan-400 font-medium">{c.strategy}.{c.param}</span>
                      <span className="text-gray-500">{c.date}</span>
                    </div>
                    <div className="font-mono text-gray-300">{c.old_value} → {c.new_value}</div>
                    {c.reason && <div className="text-gray-500 mt-0.5">{c.reason.slice(0, 100)}</div>}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-600 text-sm">No changes yet. The agent will tune parameters after collecting trade data.</div>
            )}
          </div>
        </div>
      </div>

      {/* Performers */}
      {(performers.outperformers?.length > 0 || performers.underperformers?.length > 0) && (
        <div className="grid grid-cols-2 gap-6 mb-6">
          <div className="bg-green-900/10 rounded-xl p-5 border border-green-500/20">
            <h3 className="text-sm font-semibold text-green-400 mb-3">Outperformers</h3>
            {(performers.outperformers || []).map((o: any, i: number) => (
              <div key={i} className="text-sm mb-2">
                <span className="text-white font-medium">{o.strategy}</span>
                <span className="text-green-400 text-xs ml-2">{o.reason}</span>
              </div>
            ))}
            {!performers.outperformers?.length && <div className="text-gray-600 text-sm">None yet</div>}
          </div>
          <div className="bg-red-900/10 rounded-xl p-5 border border-red-500/20">
            <h3 className="text-sm font-semibold text-red-400 mb-3">Underperformers</h3>
            {(performers.underperformers || []).map((u: any, i: number) => (
              <div key={i} className="text-sm mb-2">
                <span className="text-white font-medium">{u.strategy}</span>
                <span className="text-red-400 text-xs ml-2">{u.reason}</span>
              </div>
            ))}
            {!performers.underperformers?.length && <div className="text-gray-600 text-sm">None yet</div>}
          </div>
        </div>
      )}

      {/* Manual Controls */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">Manual Controls</h3>
        <div className="flex gap-3">
          <button onClick={() => runCycle('daily')} disabled={loading}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-500 disabled:opacity-50">
            Run Daily Cycle
          </button>
          <button onClick={() => runCycle('weekly')} disabled={loading}
            className="px-4 py-2 rounded-lg bg-purple-600 text-white text-sm hover:bg-purple-500 disabled:opacity-50">
            Run Weekly Review
          </button>
          <span className="text-xs text-gray-600 self-center">
            Last daily: {status.last_daily ? new Date(status.last_daily).toLocaleString() : 'never'} |
            Last weekly: {status.last_weekly ? new Date(status.last_weekly).toLocaleString() : 'never'}
          </span>
        </div>
      </div>
    </div>
  )
}
