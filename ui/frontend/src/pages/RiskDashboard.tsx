import { useState, useEffect } from 'react'
import api from '../api/client'
import type { RiskDashboardData, PaperPortfolio } from '../api/signals-types'

function EditableField({ label, value, onChange, suffix = '', prefix = '', min, max, step = 1, hint }: {
  label: string, value: number, onChange: (v: number) => void,
  suffix?: string, prefix?: string, min?: number, max?: number, step?: number, hint?: string
}) {
  return (
    <div>
      <label className="text-[10px] text-gray-500 uppercase tracking-wider block mb-1">{label}</label>
      <div className="flex items-center gap-1">
        {prefix && <span className="text-gray-500 text-sm">{prefix}</span>}
        <input
          type="number" value={value} min={min} max={max} step={step}
          onChange={e => onChange(Number(e.target.value))}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm font-mono text-white w-24 focus:border-blue-500 focus:outline-none"
        />
        {suffix && <span className="text-gray-500 text-sm">{suffix}</span>}
      </div>
      {hint && <div className="text-[9px] text-gray-600 mt-0.5">{hint}</div>}
    </div>
  )
}

function GaugeCircle({ value, max, label, color }: { value: number, max: number, label: string, color: string }) {
  const pct = Math.min((Math.abs(value) / max) * 100, 100)
  const circumference = 2 * Math.PI * 40
  const offset = circumference - (pct / 100) * circumference
  const strokeColor = pct > 75 ? '#ef4444' : pct > 50 ? '#f59e0b' : color

  return (
    <div className="flex flex-col items-center">
      <svg width="100" height="100" className="-rotate-90">
        <circle cx="50" cy="50" r="40" fill="none" stroke="#374151" strokeWidth="8" />
        <circle cx="50" cy="50" r="40" fill="none" stroke={strokeColor} strokeWidth="8"
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" className="transition-all duration-500" />
      </svg>
      <div className="text-center -mt-16 mb-4">
        <div className="text-xl font-bold font-mono text-white">{pct.toFixed(0)}%</div>
      </div>
      <div className="text-xs text-gray-400 mt-2">{label}</div>
    </div>
  )
}

export default function RiskDashboard() {
  const [risk, setRisk] = useState<RiskDashboardData | null>(null)
  const [paper, setPaper] = useState<PaperPortfolio | null>(null)
  const [config, setConfig] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [dirty, setDirty] = useState(false)

  // Editable state
  const [fxBalance, setFxBalance] = useState(500)
  const [fxRiskPct, setFxRiskPct] = useState(2)
  const [fxDailyLimit, setFxDailyLimit] = useState(3)
  const [fxMaxPos, setFxMaxPos] = useState(2)
  const [fxStopMult, setFxStopMult] = useState(1.5)
  const [optBalance, setOptBalance] = useState(500)
  const [optRiskPct, setOptRiskPct] = useState(8)
  const [optDailyLimit, setOptDailyLimit] = useState(3)
  const [optMaxPos, setOptMaxPos] = useState(3)
  const [optMinDTE, setOptMinDTE] = useState(7)
  const [optMaxPrice, setOptMaxPrice] = useState(3)
  const [portMaxRisk, setPortMaxRisk] = useState(10)

  useEffect(() => {
    Promise.all([
      api.get('/risk/dashboard'),
      api.get('/trading/paper/portfolio'),
      api.get('/risk/config'),
    ]).then(([riskRes, paperRes, configRes]) => {
      setRisk(riskRes.data)
      setPaper(paperRes.data)
      const c = configRes.data
      setConfig(c)
      // Populate editable fields from config
      setFxBalance(c.forex?.account_balance ?? 500)
      setFxRiskPct(c.forex?.max_risk_per_trade_pct ?? 2)
      setFxDailyLimit(c.forex?.daily_loss_limit_pct ?? 3)
      setFxMaxPos(c.forex?.max_concurrent_positions ?? 2)
      setFxStopMult(c.forex?.stop_multiplier ?? 1.5)
      setOptBalance(c.options?.account_balance ?? 500)
      setOptRiskPct(c.options?.max_risk_per_trade_pct ?? 8)
      setOptDailyLimit(c.options?.daily_loss_limit_pct ?? 3)
      setOptMaxPos(c.options?.max_concurrent_positions ?? 3)
      setOptMinDTE(c.options?.min_days_to_expiry ?? 7)
      setOptMaxPrice(c.options?.max_option_price ?? 3)
      setPortMaxRisk(c.portfolio?.max_total_risk_pct ?? 10)
    }).catch(() => {})
  }, [])

  const markDirty = (setter: (v: any) => void) => (v: any) => { setter(v); setDirty(true) }

  const saveConfig = async () => {
    setSaving(true)
    setMessage('')
    try {
      const res = await api.put('/risk/config', {
        forex_balance: fxBalance,
        forex_risk_per_trade_pct: fxRiskPct,
        forex_daily_loss_limit_pct: fxDailyLimit,
        forex_max_positions: fxMaxPos,
        forex_stop_multiplier: fxStopMult,
        options_balance: optBalance,
        options_risk_per_trade_pct: optRiskPct,
        options_daily_loss_limit_pct: optDailyLimit,
        options_max_positions: optMaxPos,
        options_min_dte: optMinDTE,
        options_max_option_price: optMaxPrice,
        portfolio_max_total_risk_pct: portMaxRisk,
      })
      setDirty(false)
      setMessage(`Saved. Forex: $${res.data.computed.forex_max_risk_per_trade}/trade, Options: $${res.data.computed.options_max_risk_per_trade}/trade, Total capital: $${res.data.computed.total_capital}`)
      // Refresh dashboard
      const riskRes = await api.get('/risk/dashboard')
      setRisk(riskRes.data)
    } catch (e: any) {
      setMessage(e.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (!risk) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-500">Loading...</div>
  )

  // Computed values for display
  const fxMaxRisk = fxBalance * fxRiskPct / 100
  const fxDailyMax = fxBalance * fxDailyLimit / 100
  const optMaxRisk = optBalance * optRiskPct / 100
  const optDailyMax = optBalance * optDailyLimit / 100
  const totalCapital = fxBalance + optBalance

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Risk Management</h1>
          <p className="text-gray-500 text-sm">Configure your risk profiles and monitor exposure</p>
        </div>
        <div className="flex items-center gap-3">
          {dirty && (
            <span className="text-xs text-amber-400 animate-pulse">Unsaved changes</span>
          )}
          <button
            onClick={saveConfig}
            disabled={saving || !dirty}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
              dirty ? 'bg-blue-600 text-white hover:bg-blue-500' : 'bg-gray-800 text-gray-600 cursor-not-allowed'
            }`}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {message && (
        <div className="mb-4 px-4 py-2 rounded-lg bg-gray-800 text-sm text-gray-300 border border-gray-700">{message}</div>
      )}

      {/* Live Status Gauges */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        {/* Forex Gauges */}
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-blue-400">Forex (TastyFX)</h2>
            <span className={`text-xs px-2 py-1 rounded font-medium ${
              risk.forex.trading_paused ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'
            }`}>
              {risk.forex.trading_paused ? 'PAUSED' : 'ACTIVE'}
            </span>
          </div>
          <div className="flex items-center justify-around mb-4">
            <GaugeCircle value={risk.forex.daily_risk_used_pct} max={100} label="Daily Risk Used" color="#3b82f6" />
            <GaugeCircle value={risk.forex.open_positions} max={fxMaxPos} label="Position Slots" color="#3b82f6" />
          </div>
          <div className="text-center text-sm text-gray-400 mb-2">
            Balance: <span className="text-white font-mono font-bold">${risk.forex.account_balance.toFixed(0)}</span>
            {' '} | Today: <span className={`font-mono ${risk.forex.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {risk.forex.daily_pnl >= 0 ? '+' : ''}${risk.forex.daily_pnl.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Options Gauges */}
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-purple-400">Options (Tastytrade)</h2>
            <span className={`text-xs px-2 py-1 rounded font-medium ${
              risk.options.trading_paused ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'
            }`}>
              {risk.options.trading_paused ? 'PAUSED' : 'ACTIVE'}
            </span>
          </div>
          <div className="flex items-center justify-around mb-4">
            <GaugeCircle value={risk.options.daily_risk_used_pct} max={100} label="Daily Risk Used" color="#a855f7" />
            <GaugeCircle value={risk.options.open_positions} max={optMaxPos} label="Position Slots" color="#a855f7" />
          </div>
          <div className="text-center text-sm text-gray-400 mb-2">
            Balance: <span className="text-white font-mono font-bold">${risk.options.account_balance.toFixed(0)}</span>
            {' '} | Today: <span className={`font-mono ${risk.options.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {risk.options.daily_pnl >= 0 ? '+' : ''}${risk.options.daily_pnl.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Editable Risk Profiles */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        {/* Forex Profile */}
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <h3 className="text-sm font-bold text-blue-400 uppercase tracking-wider mb-4">Forex Risk Profile</h3>
          <div className="grid grid-cols-2 gap-4">
            <EditableField label="Account Balance" value={fxBalance} prefix="$" onChange={markDirty(setFxBalance)} min={100} max={100000} step={100}
              hint="Your TastyFX account size" />
            <EditableField label="Risk Per Trade" value={fxRiskPct} suffix="%" onChange={markDirty(setFxRiskPct)} min={0.5} max={10} step={0.5}
              hint={`= $${fxMaxRisk.toFixed(0)} per trade`} />
            <EditableField label="Daily Loss Limit" value={fxDailyLimit} suffix="%" onChange={markDirty(setFxDailyLimit)} min={1} max={20} step={0.5}
              hint={`= $${fxDailyMax.toFixed(0)} max daily loss`} />
            <EditableField label="Max Positions" value={fxMaxPos} onChange={markDirty(setFxMaxPos)} min={1} max={10}
              hint="Concurrent open trades" />
            <EditableField label="Stop ATR Multiplier" value={fxStopMult} suffix="x" onChange={markDirty(setFxStopMult)} min={0.5} max={5} step={0.1}
              hint="ATR multiplier for stop distance" />
          </div>
          {/* Computed summary */}
          <div className="mt-4 bg-gray-800 rounded-lg p-3 grid grid-cols-3 gap-2 text-center text-xs">
            <div>
              <div className="text-gray-500">Per Trade</div>
              <div className="text-white font-mono font-bold">${fxMaxRisk.toFixed(0)}</div>
            </div>
            <div>
              <div className="text-gray-500">Daily Limit</div>
              <div className="text-white font-mono font-bold">${fxDailyMax.toFixed(0)}</div>
            </div>
            <div>
              <div className="text-gray-500">Max Exposure</div>
              <div className="text-white font-mono font-bold">${(fxMaxRisk * fxMaxPos).toFixed(0)}</div>
            </div>
          </div>
        </div>

        {/* Options Profile */}
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <h3 className="text-sm font-bold text-purple-400 uppercase tracking-wider mb-4">Options Risk Profile</h3>
          <div className="grid grid-cols-2 gap-4">
            <EditableField label="Account Balance" value={optBalance} prefix="$" onChange={markDirty(setOptBalance)} min={100} max={100000} step={100}
              hint="Your Tastytrade account size" />
            <EditableField label="Risk Per Trade" value={optRiskPct} suffix="%" onChange={markDirty(setOptRiskPct)} min={1} max={20} step={1}
              hint={`= $${optMaxRisk.toFixed(0)} per trade`} />
            <EditableField label="Daily Loss Limit" value={optDailyLimit} suffix="%" onChange={markDirty(setOptDailyLimit)} min={1} max={20} step={0.5}
              hint={`= $${optDailyMax.toFixed(0)} max daily loss`} />
            <EditableField label="Max Positions" value={optMaxPos} onChange={markDirty(setOptMaxPos)} min={1} max={10}
              hint="Concurrent open trades" />
            <EditableField label="Min Days to Expiry" value={optMinDTE} suffix="DTE" onChange={markDirty(setOptMinDTE)} min={1} max={90}
              hint="No options expiring sooner" />
            <EditableField label="Max Option Price" value={optMaxPrice} prefix="$" onChange={markDirty(setOptMaxPrice)} min={0.5} max={20} step={0.5}
              hint="Max premium per contract" />
          </div>
          <div className="mt-4 bg-gray-800 rounded-lg p-3 grid grid-cols-3 gap-2 text-center text-xs">
            <div>
              <div className="text-gray-500">Per Trade</div>
              <div className="text-white font-mono font-bold">${optMaxRisk.toFixed(0)}</div>
            </div>
            <div>
              <div className="text-gray-500">Daily Limit</div>
              <div className="text-white font-mono font-bold">${optDailyMax.toFixed(0)}</div>
            </div>
            <div>
              <div className="text-gray-500">Max Exposure</div>
              <div className="text-white font-mono font-bold">${(optMaxRisk * optMaxPos).toFixed(0)}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Portfolio Level */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 mb-8">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">Portfolio Settings</h3>
        <div className="grid grid-cols-4 gap-6 items-end">
          <EditableField label="Max Total Risk" value={portMaxRisk} suffix="% of capital" onChange={markDirty(setPortMaxRisk)} min={5} max={50} step={1}
            hint={`= $${(totalCapital * portMaxRisk / 100).toFixed(0)} max at risk`} />
          <div className="bg-gray-800 rounded-lg p-3 text-center">
            <div className="text-[10px] text-gray-500 uppercase">Total Capital</div>
            <div className="text-2xl font-bold font-mono">${totalCapital.toFixed(0)}</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-3 text-center">
            <div className="text-[10px] text-gray-500 uppercase">Today P&L</div>
            <div className={`text-2xl font-bold font-mono ${risk.portfolio.total_daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {risk.portfolio.total_daily_pnl >= 0 ? '+' : ''}${risk.portfolio.total_daily_pnl.toFixed(2)}
            </div>
          </div>
          <div className="bg-gray-800 rounded-lg p-3 text-center">
            <div className="text-[10px] text-gray-500 uppercase">Open Positions</div>
            <div className="text-2xl font-bold font-mono">{risk.portfolio.total_positions}</div>
          </div>
        </div>
      </div>

      {/* Paper Trading Graduation */}
      {paper && (
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Paper Trading Progress</h3>
            <span className={`text-sm px-3 py-1 rounded-full font-medium ${
              paper.ready_for_live ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'
            }`}>
              {paper.ready_for_live ? 'Ready for Live' : 'Paper Mode'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-6">
            {(['forex', 'options'] as const).map(key => {
              const acct = paper[key]
              const progress = Math.min((acct.stats.total_trades / 50) * 100, 100)
              return (
                <div key={key}>
                  <div className="text-sm font-medium text-gray-400 mb-2 capitalize">{key}</div>
                  <div className="flex items-center gap-4 mb-2">
                    <div className="text-sm font-mono">{acct.stats.total_trades}/50 trades</div>
                    <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${progress}%` }} />
                    </div>
                  </div>
                  <div className="flex gap-4 text-xs text-gray-500">
                    <span>Win Rate: <span className={acct.stats.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}>
                      {acct.stats.win_rate}%
                    </span></span>
                    <span>Balance: <span className="text-white font-mono">${acct.balance.toFixed(2)}</span></span>
                    <span>Return: <span className={acct.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
                      {acct.return_pct}%
                    </span></span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
