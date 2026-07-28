import { useState } from 'react'
import api from '../api/client'
import type { BacktestResult } from '../api/signals-types'

const presets = [
  { label: 'USD/JPY (Forex)', symbol: 'JPY=X', asset_type: 'forex' },
  { label: 'SPY (Options)', symbol: 'SPY', asset_type: 'options' },
  { label: 'AAPL (Options)', symbol: 'AAPL', asset_type: 'options' },
]

export default function Backtesting() {
  const [symbol, setSymbol] = useState('JPY=X')
  const [assetType, setAssetType] = useState('forex')
  const [months, setMonths] = useState(6)
  const [balance, setBalance] = useState(500)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [error, setError] = useState('')

  const runBacktest = async () => {
    setRunning(true)
    setError('')
    setResult(null)
    try {
      const res = await api.post('/signals/backtest', {
        symbol, asset_type: assetType,
        lookback_months: months, start_balance: balance,
      })
      setResult(res.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Backtest failed')
    } finally {
      setRunning(false)
    }
  }

  const maxEquity = result ? Math.max(...result.equity_curve.map(e => e.equity)) : 0
  const minEquity = result ? Math.min(...result.equity_curve.map(e => e.equity)) : 0
  const equityRange = maxEquity - minEquity || 1

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <h1 className="text-2xl font-bold mb-1">Strategy Backtester</h1>
      <p className="text-gray-500 text-sm mb-6">Prove a strategy works before risking real money</p>

      {/* Config */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Preset</label>
            <div className="flex gap-2">
              {presets.map(p => (
                <button
                  key={p.symbol}
                  onClick={() => { setSymbol(p.symbol); setAssetType(p.asset_type) }}
                  className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                    symbol === p.symbol ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Lookback (months)</label>
            <select value={months} onChange={e => setMonths(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
              <option value={3}>3 months</option>
              <option value={6}>6 months</option>
              <option value={9}>9 months</option>
              <option value={12}>12 months</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Starting Balance</label>
            <input type="number" value={balance} onChange={e => setBalance(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-28" />
          </div>
          <button
            onClick={runBacktest}
            disabled={running}
            className="px-6 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 disabled:opacity-50"
          >
            {running ? 'Running...' : 'Run Backtest'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-900/30 text-red-400 text-sm border border-red-800">{error}</div>
      )}

      {result && (
        <>
          {/* Results Summary */}
          <div className={`rounded-xl p-6 border mb-6 ${
            result.passes_gate ? 'bg-green-900/10 border-green-500/30' : 'bg-red-900/10 border-red-500/30'
          }`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Backtest Results: {result.symbol}</h2>
              <span className={`text-sm px-3 py-1 rounded-full font-bold ${
                result.passes_gate ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
              }`}>
                {result.passes_gate ? 'PASSES GATE' : 'FAILS GATE'}
              </span>
            </div>

            <div className="grid grid-cols-6 gap-4">
              <div className="bg-black/20 rounded-lg p-4">
                <div className="text-xs text-gray-500">Final Balance</div>
                <div className={`text-xl font-bold font-mono ${result.final_balance >= result.start_balance ? 'text-green-400' : 'text-red-400'}`}>
                  ${result.final_balance.toFixed(0)}
                </div>
                <div className={`text-xs font-mono ${result.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {result.total_return_pct >= 0 ? '+' : ''}{result.total_return_pct}%
                </div>
              </div>
              <div className="bg-black/20 rounded-lg p-4">
                <div className="text-xs text-gray-500">Win Rate</div>
                <div className={`text-xl font-bold font-mono ${result.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                  {result.win_rate}%
                </div>
                <div className="text-xs text-gray-500">{result.wins}W / {result.losses}L</div>
              </div>
              <div className="bg-black/20 rounded-lg p-4">
                <div className="text-xs text-gray-500">Total Trades</div>
                <div className="text-xl font-bold font-mono">{result.total_trades}</div>
                <div className="text-xs text-gray-500">{result.lookback_months}mo period</div>
              </div>
              <div className="bg-black/20 rounded-lg p-4">
                <div className="text-xs text-gray-500">Avg R Multiple</div>
                <div className={`text-xl font-bold font-mono ${result.avg_r_multiple >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {result.avg_r_multiple >= 0 ? '+' : ''}{result.avg_r_multiple}R
                </div>
              </div>
              <div className="bg-black/20 rounded-lg p-4">
                <div className="text-xs text-gray-500">Profit Factor</div>
                <div className={`text-xl font-bold font-mono ${Number(result.profit_factor) > 1 ? 'text-green-400' : 'text-red-400'}`}>
                  {result.profit_factor}
                </div>
              </div>
              <div className="bg-black/20 rounded-lg p-4">
                <div className="text-xs text-gray-500">Max Drawdown</div>
                <div className="text-xl font-bold font-mono text-red-400">
                  -{result.max_drawdown_pct}%
                </div>
              </div>
            </div>
          </div>

          {/* Equity Curve */}
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 mb-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-4">Equity Curve</h3>
            <div className="h-48 flex items-end gap-px">
              {result.equity_curve.map((point, i) => {
                const height = ((point.equity - minEquity) / equityRange) * 100
                const color = point.equity >= result.start_balance ? 'bg-green-500' : 'bg-red-500'
                return (
                  <div
                    key={i}
                    className={`flex-1 ${color} rounded-t-sm opacity-80 hover:opacity-100 transition-opacity`}
                    style={{ height: `${Math.max(height, 1)}%` }}
                    title={`${point.date}: $${point.equity.toFixed(2)}`}
                  />
                )
              })}
            </div>
            <div className="flex justify-between text-xs text-gray-600 mt-2">
              <span>{result.equity_curve[0]?.date}</span>
              <span className="text-gray-500">
                ${minEquity.toFixed(0)} - ${maxEquity.toFixed(0)}
              </span>
              <span>{result.equity_curve[result.equity_curve.length - 1]?.date}</span>
            </div>
          </div>

          {/* Trade List */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <div className="px-6 py-3 bg-gray-800 text-sm font-semibold text-gray-400">
              Trade History ({result.trades.length} trades)
            </div>
            <div className="max-h-96 overflow-y-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 text-xs uppercase tracking-wider">
                    <th className="px-4 py-2 text-left">Date</th>
                    <th className="px-4 py-2 text-left">Dir</th>
                    <th className="px-4 py-2 text-right">Entry</th>
                    <th className="px-4 py-2 text-right">Exit</th>
                    <th className="px-4 py-2 text-right">P&L</th>
                    <th className="px-4 py-2 text-right">R</th>
                    <th className="px-4 py-2 text-center">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((t, i) => (
                    <tr key={i} className="border-t border-gray-800">
                      <td className="px-4 py-2 text-gray-400">{t.date}</td>
                      <td className={`px-4 py-2 font-bold ${t.direction === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                        {t.direction}
                      </td>
                      <td className="px-4 py-2 text-right font-mono">{t.entry.toFixed(2)}</td>
                      <td className="px-4 py-2 text-right font-mono">{t.exit.toFixed(2)}</td>
                      <td className={`px-4 py-2 text-right font-mono font-bold ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)}
                      </td>
                      <td className={`px-4 py-2 text-right font-mono ${t.r_multiple >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {t.r_multiple >= 0 ? '+' : ''}{t.r_multiple.toFixed(1)}R
                      </td>
                      <td className="px-4 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          t.outcome === 'win' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          {t.outcome.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Gate Requirements */}
          <div className="mt-6 bg-gray-900 rounded-xl p-6 border border-gray-800">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Gate Requirements</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className={result.total_trades >= (result.gate_requirements.min_trades || 50) ? 'text-green-400' : 'text-red-400'}>
                  {result.total_trades >= (result.gate_requirements.min_trades || 50) ? '\u2713' : '\u2717'}
                </span>
                <span className="text-gray-400">Min {result.gate_requirements.min_trades || 50} trades</span>
                <span className="font-mono text-white">(got {result.total_trades})</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={result.win_rate >= (result.gate_requirements.min_win_rate || 50) ? 'text-green-400' : 'text-red-400'}>
                  {result.win_rate >= (result.gate_requirements.min_win_rate || 50) ? '\u2713' : '\u2717'}
                </span>
                <span className="text-gray-400">Min {result.gate_requirements.min_win_rate || 50}% win rate</span>
                <span className="font-mono text-white">(got {result.win_rate}%)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={result.avg_r_multiple >= (result.gate_requirements.min_risk_reward || 2) ? 'text-green-400' : 'text-red-400'}>
                  {result.avg_r_multiple >= (result.gate_requirements.min_risk_reward || 2) ? '\u2713' : '\u2717'}
                </span>
                <span className="text-gray-400">Min {result.gate_requirements.min_risk_reward || 2}:1 R/R</span>
                <span className="font-mono text-white">(avg {result.avg_r_multiple}R)</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
