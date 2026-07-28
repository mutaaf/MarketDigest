import { useState, useEffect, useCallback } from 'react'
import api from '../api/client'
import type { PaperPortfolio, JournalEntry } from '../api/signals-types'

export default function PaperTrading() {
  const [portfolio, setPortfolio] = useState<PaperPortfolio | null>(null)
  const [journal, setJournal] = useState<JournalEntry[]>([])
  const [activeTab, setActiveTab] = useState<'positions' | 'journal'>('positions')
  const [message, setMessage] = useState('')

  const refresh = useCallback(async () => {
    try {
      const [portRes, journalRes] = await Promise.all([
        api.get('/trading/paper/portfolio'),
        api.get('/trading/paper/journal'),
      ])
      setPortfolio(portRes.data)
      setJournal(journalRes.data.trades || [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const autoTrade = async () => {
    setMessage('Auto-trading signals...')
    try {
      const res = await api.post('/trading/paper/auto-trade')
      setMessage(`Auto-traded ${res.data.traded} signals`)
      refresh()
    } catch (e: any) {
      setMessage(e.response?.data?.detail || 'Auto-trade failed')
    }
  }

  const resetPortfolio = async () => {
    if (!confirm('Reset paper portfolio? All trades will be lost.')) return
    try {
      await api.post('/trading/paper/reset')
      setMessage('Portfolio reset to $500/$500')
      refresh()
    } catch { setMessage('Reset failed') }
  }

  if (!portfolio) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-500">Loading...</div>
  )

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Paper Trading</h1>
          <p className="text-gray-500 text-sm">Practice trading without risking real money</p>
        </div>
        <div className="flex gap-3">
          <button onClick={autoTrade}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 transition-colors">
            Auto-Trade Signals
          </button>
          <button onClick={resetPortfolio}
            className="px-4 py-2 rounded-lg bg-gray-700 text-gray-300 text-sm font-medium hover:bg-gray-600 transition-colors">
            Reset
          </button>
        </div>
      </div>

      {message && (
        <div className="mb-4 px-4 py-2 rounded-lg bg-gray-800 text-sm text-gray-300 border border-gray-700">{message}</div>
      )}

      {/* Account Cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {(['forex', 'options'] as const).map(key => {
          const acct = portfolio[key]
          const returnPct = acct.return_pct
          return (
            <div key={key} className="bg-gray-900 rounded-xl p-5 border border-gray-800">
              <div className="text-sm text-gray-400 capitalize mb-1">{key} Paper Account</div>
              <div className="text-3xl font-bold font-mono">${acct.balance.toFixed(2)}</div>
              <div className={`text-sm font-mono mt-1 ${returnPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {returnPct >= 0 ? '+' : ''}{returnPct}% return
              </div>
              <div className="grid grid-cols-3 gap-2 mt-4 text-xs">
                <div className="bg-gray-800 rounded p-2 text-center">
                  <div className="text-gray-500">Trades</div>
                  <div className="font-mono font-bold">{acct.stats.total_trades}</div>
                </div>
                <div className="bg-gray-800 rounded p-2 text-center">
                  <div className="text-gray-500">Win Rate</div>
                  <div className={`font-mono font-bold ${acct.stats.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                    {acct.stats.win_rate}%
                  </div>
                </div>
                <div className="bg-gray-800 rounded p-2 text-center">
                  <div className="text-gray-500">P&L</div>
                  <div className={`font-mono font-bold ${acct.stats.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${acct.stats.total_pnl.toFixed(0)}
                  </div>
                </div>
              </div>
            </div>
          )
        })}

        {/* Graduation Card */}
        <div className={`rounded-xl p-5 border ${
          portfolio.ready_for_live
            ? 'bg-green-900/20 border-green-500/30'
            : 'bg-gray-900 border-gray-800'
        }`}>
          <div className="text-sm text-gray-400 mb-1">Live Trading Gate</div>
          <div className={`text-2xl font-bold ${portfolio.ready_for_live ? 'text-green-400' : 'text-amber-400'}`}>
            {portfolio.ready_for_live ? 'UNLOCKED' : 'LOCKED'}
          </div>
          <div className="text-xs text-gray-500 mt-2">
            Need 50+ trades with &gt;50% win rate in both accounts to unlock live trading.
          </div>
          <div className="mt-3 space-y-1">
            {(['forex', 'options'] as const).map(key => {
              const s = portfolio[key].stats
              const tradePassed = s.total_trades >= 50
              const wrPassed = s.win_rate >= 50
              return (
                <div key={key} className="flex items-center gap-2 text-xs">
                  <span className={tradePassed && wrPassed ? 'text-green-400' : 'text-gray-500'}>
                    {tradePassed && wrPassed ? '\u2713' : '\u25CB'}
                  </span>
                  <span className="capitalize text-gray-400">{key}:</span>
                  <span className={tradePassed ? 'text-green-400' : 'text-gray-500'}>{s.total_trades}/50 trades</span>
                  <span className={wrPassed ? 'text-green-400' : 'text-gray-500'}>{s.win_rate}% WR</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-gray-900 rounded-lg p-1 w-fit">
        {(['positions', 'journal'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors capitalize ${
              activeTab === tab ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Open Positions */}
      {activeTab === 'positions' && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-800 text-gray-400 text-xs uppercase tracking-wider">
                <th className="px-4 py-3 text-left">Symbol</th>
                <th className="px-4 py-3 text-left">Direction</th>
                <th className="px-4 py-3 text-right">Entry</th>
                <th className="px-4 py-3 text-right">Stop</th>
                <th className="px-4 py-3 text-right">Target</th>
                <th className="px-4 py-3 text-right">R/R</th>
                <th className="px-4 py-3 text-right">Risk</th>
                <th className="px-4 py-3 text-center">Grade</th>
              </tr>
            </thead>
            <tbody>
              {[...portfolio.forex.open_trades, ...portfolio.options.open_trades].map(t => (
                <tr key={t.id} className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="px-4 py-3 font-mono font-bold">{t.symbol}</td>
                  <td className={`px-4 py-3 font-bold ${t.direction === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                    {t.direction}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">{t.entry_price}</td>
                  <td className="px-4 py-3 text-right font-mono text-red-300">{t.stop_loss}</td>
                  <td className="px-4 py-3 text-right font-mono text-green-300">{t.target_1}</td>
                  <td className="px-4 py-3 text-right font-mono text-amber-400">{t.risk_reward}:1</td>
                  <td className="px-4 py-3 text-right font-mono">${t.dollar_risk}</td>
                  <td className="px-4 py-3 text-center font-bold">{t.grade}</td>
                </tr>
              ))}
              {portfolio.forex.open_trades.length + portfolio.options.open_trades.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-600">
                    No open paper trades. Click "Auto-Trade Signals" or paper trade from the Signal Terminal.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Trade Journal */}
      {activeTab === 'journal' && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-800 text-gray-400 text-xs uppercase tracking-wider">
                <th className="px-4 py-3 text-left">Date</th>
                <th className="px-4 py-3 text-left">Symbol</th>
                <th className="px-4 py-3 text-left">Direction</th>
                <th className="px-4 py-3 text-right">Entry</th>
                <th className="px-4 py-3 text-right">Exit</th>
                <th className="px-4 py-3 text-right">P&L</th>
                <th className="px-4 py-3 text-right">R Multiple</th>
                <th className="px-4 py-3 text-center">Result</th>
              </tr>
            </thead>
            <tbody>
              {journal.slice().reverse().map((t, i) => (
                <tr key={i} className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-gray-400 text-xs">{new Date(t.exit_time).toLocaleDateString()}</td>
                  <td className="px-4 py-3 font-mono font-bold">{t.symbol}</td>
                  <td className={`px-4 py-3 font-bold ${t.direction === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                    {t.direction}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">{t.entry_price}</td>
                  <td className="px-4 py-3 text-right font-mono">{t.exit_price}</td>
                  <td className={`px-4 py-3 text-right font-mono font-bold ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 text-right font-mono ${t.r_multiple >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {t.r_multiple >= 0 ? '+' : ''}{t.r_multiple.toFixed(1)}R
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      t.outcome === 'win' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                    }`}>
                      {t.outcome.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
              {journal.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-600">
                    No completed trades yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
