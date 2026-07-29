// Compass — Retirement: a plan you play with. Sliders recompute your future
// instantly; the Monte Carlo "chance it works" syncs quietly in the background.
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { MessageCircleQuestion, PartyPopper } from 'lucide-react'
import api from '../api/client'
import {
  EmptyState, ErrorState, MoneyInput, PageSkeleton, ScoreRing, money,
  useCountUp, usePortfolioSelection, withCommas,
} from '../components/compass/ui'

interface Inputs {
  current_age: number
  retire_age: number
  current_assets: number
  monthly_contribution: number
  monthly_spending: number
  expected_return_pct: number
}

const DEFAULTS: Inputs = {
  current_age: 35, retire_age: 65, current_assets: 0,
  monthly_contribution: 500, monthly_spending: 4000, expected_return_pct: 7,
}
const INFLATION = 2.5

/** Mirror of the server's deterministic math — instant slider feedback. */
function projectLocal(inp: Inputs) {
  const years = Math.max(0, inp.retire_age - inp.current_age)
  const realReturn = (1 + inp.expected_return_pct / 100) / (1 + INFLATION / 100) - 1
  const path: { age: number; balance: number }[] = []
  let balance = inp.current_assets
  let millionAge: number | null = null
  for (let y = 0; y <= years; y++) {
    path.push({ age: inp.current_age + y, balance: Math.round(balance) })
    if (millionAge === null && balance >= 1_000_000) millionAge = inp.current_age + y
    balance = balance * (1 + realReturn) + inp.monthly_contribution * 12
  }
  const projected = path[path.length - 1]?.balance ?? inp.current_assets
  return { path, projected, safeMonthly: Math.round(projected * 0.04 / 12), millionAge }
}

function SliderRow({ label, value, display, min, max, step, onChange }: {
  label: string; value: number; display: string
  min: number; max: number; step: number; onChange: (v: number) => void
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-sm text-apple-gray-600">{label}</span>
        <span className="text-sm font-semibold tabular-nums text-apple-gray-800">{display}</span>
      </div>
      <input type="range" className="compass-slider" min={min} max={max} step={step}
        value={value} onChange={e => onChange(parseFloat(e.target.value))} />
    </div>
  )
}

export default function CompassRetire() {
  const { portfolios, selected, error: listError, refresh: refreshList } = usePortfolioSelection()
  const [inputs, setInputs] = useState<Inputs | null>(null)
  const [assetsText, setAssetsText] = useState('')
  const [successProb, setSuccessProb] = useState<number | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [picked, setPicked] = useState<{ age: number; balance: number } | null>(null)
  const saveTimer = useRef<number>()

  // Load saved plan (assets prefilled from portfolio when no plan exists yet)
  useEffect(() => {
    if (!selected) return
    setInputs(null); setSuccessProb(null); setError(null)
    api.get(`/portfolio/${selected}/retirement`, { timeout: 60000 })
      .then(res => {
        const saved = res.data.inputs || {}
        const merged: Inputs = {
          ...DEFAULTS,
          ...Object.fromEntries(Object.entries(saved).filter(([, v]) => v !== null && v !== undefined)),
        }
        merged.current_assets = Math.round(merged.current_assets)
        setInputs(merged)
        setAssetsText(String(merged.current_assets || ''))
        if (res.data.projection?.success_probability != null) {
          setSuccessProb(res.data.projection.success_probability)
        }
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [selected])

  // Quietly sync to the server (saves the plan + runs the Monte Carlo)
  useEffect(() => {
    if (!inputs || !selected || inputs.retire_age <= inputs.current_age) return
    window.clearTimeout(saveTimer.current)
    setSyncing(true)
    saveTimer.current = window.setTimeout(() => {
      api.post(`/portfolio/${selected}/retirement`, {
        ...inputs, inflation_pct: INFLATION,
      }, { timeout: 60000 })
        .then(res => setSuccessProb(res.data.projection?.success_probability ?? null))
        .catch(() => { /* local math still works; probability just stays put */ })
        .finally(() => setSyncing(false))
    }, 800)
    return () => window.clearTimeout(saveTimer.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputs])

  const local = useMemo(() => inputs ? projectLocal(inputs) : null, [inputs])
  const animatedProjected = useCountUp(local?.projected ?? 0)
  const animatedSafe = useCountUp(local?.safeMonthly ?? 0)

  if (listError) return <ErrorState message={listError} onRetry={refreshList} />
  if (portfolios && portfolios.length === 0) {
    return <EmptyState title="No portfolio yet" hint="Create your portfolio first — then plan your retirement here." />
  }
  if (!inputs && !error) return <PageSkeleton />
  if (error) return <ErrorState message={error} />
  if (!inputs || !local) return null

  const set = (patch: Partial<Inputs>) => setInputs({ ...inputs, ...patch })
  const gap = successProb === null ? null : successProb >= 85 ? 'good' : successProb >= 60 ? 'close' : 'short'
  const maxBalance = Math.max(...local.path.map(p => p.balance), 1)
  const chartPath = local.path.filter((_, i, arr) => arr.length <= 32 || i % Math.ceil(arr.length / 32) === 0 || i === arr.length - 1)

  return (
    <div className="mx-auto max-w-3xl space-y-4 pb-6">
      <div className="animate-fadeUp">
        <h1 className="text-lg font-bold text-apple-gray-800">Retirement</h1>
        <p className="text-xs text-apple-gray-500">Drag the sliders — your future updates as you move them. All in today's dollars.</p>
      </div>

      {/* Headline result */}
      <div className="animate-fadeUp rounded-2xl border border-apple-gray-200 bg-white p-5 text-center" style={{ animationDelay: '60ms' }}>
        <p className="text-[11px] font-medium uppercase tracking-wide text-apple-gray-400">
          Projected at {inputs.retire_age}
        </p>
        <p className="mt-1 text-4xl font-bold tabular-nums text-apple-gray-800">
          {money(Math.round(animatedProjected))}
        </p>
        <p className="mt-1 text-sm text-apple-gray-500">
          could safely pay you <strong className="text-apple-gray-700">{money(Math.round(animatedSafe))}/month</strong> for life
        </p>
        {local.millionAge !== null && (
          <p className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-apple-green/10 px-3 py-1 text-xs font-medium text-green-700">
            <PartyPopper size={13} /> You cross $1,000,000 around age {local.millionAge}
          </p>
        )}
      </div>

      {/* The dials */}
      <div className="animate-fadeUp space-y-5 rounded-2xl border border-apple-gray-200 bg-white p-5" style={{ animationDelay: '120ms' }}>
        <SliderRow label="Your age" value={inputs.current_age} display={`${inputs.current_age} years`}
          min={18} max={75} step={1}
          onChange={v => set({ current_age: v, retire_age: Math.max(inputs.retire_age, v + 1) })} />
        <SliderRow label="Retire at" value={inputs.retire_age} display={`${inputs.retire_age} years`}
          min={Math.min(inputs.current_age + 1, 80)} max={80} step={1}
          onChange={v => set({ retire_age: v })} />
        <SliderRow label="Adding each month" value={inputs.monthly_contribution}
          display={`$${withCommas(String(inputs.monthly_contribution))}/mo`}
          min={0} max={10000} step={100}
          onChange={v => set({ monthly_contribution: v })} />
        <SliderRow label="Spending in retirement" value={inputs.monthly_spending}
          display={`$${withCommas(String(inputs.monthly_spending))}/mo`}
          min={1000} max={20000} step={250}
          onChange={v => set({ monthly_spending: v })} />
        <SliderRow label="Expected yearly return" value={inputs.expected_return_pct}
          display={`${inputs.expected_return_pct}%`}
          min={3} max={12} step={0.5}
          onChange={v => set({ expected_return_pct: v })} />
        <div>
          <label className="mb-1 block text-sm text-apple-gray-600">Invested so far</label>
          <MoneyInput value={assetsText} placeholder="58,000"
            onChange={raw => { setAssetsText(raw); set({ current_assets: parseFloat(raw) || 0 }) }} />
        </div>
      </div>

      {/* Chance it works */}
      <div className="animate-fadeUp flex items-center gap-4 rounded-2xl border border-apple-gray-200 bg-white p-5" style={{ animationDelay: '180ms' }}>
        <ScoreRing score={successProb ?? 0}>
          <span className={`text-lg font-bold tabular-nums ${syncing ? 'opacity-40' : ''}`}>
            {successProb !== null ? `${successProb.toFixed(0)}%` : '…'}
          </span>
        </ScoreRing>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-apple-gray-800">Chance your plan works</p>
          <p className="mt-0.5 text-xs leading-relaxed text-apple-gray-500">
            {syncing ? 'Running 1,000 market simulations…'
              : gap === 'good' ? "You're on track. Keep contributing and stay the course."
              : gap === 'close' ? 'Close — nudge the contribution slider up or retirement age later and watch this change.'
              : gap === 'short' ? 'The plan likely falls short — try moving the sliders and see what fixes it.'
              : 'Adjust the sliders to see your odds.'}
          </p>
        </div>
      </div>

      {/* Interactive growth chart */}
      <div className="animate-fadeUp rounded-2xl border border-apple-gray-200 bg-white p-4" style={{ animationDelay: '240ms' }}>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-apple-gray-400">
          How your money grows — tap a bar
        </p>
        <div className="flex h-36 items-end gap-[2px]">
          {chartPath.map((p, i) => (
            <button key={p.age}
              onClick={() => setPicked(p)}
              className={`animate-growBar flex-1 rounded-t transition-colors ${
                picked?.age === p.age ? 'bg-apple-blue' : p.balance >= 1_000_000 ? 'bg-apple-green/70' : 'bg-apple-blue/60'
              }`}
              style={{ height: `${Math.max(3, (p.balance / maxBalance) * 100)}%`, animationDelay: `${i * 14}ms` }}
            />
          ))}
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-apple-gray-400">
          <span>Age {chartPath[0]?.age}</span>
          {picked && (
            <span className="font-semibold text-apple-gray-700">
              Age {picked.age}: {money(picked.balance)}
            </span>
          )}
          <span>Age {chartPath[chartPath.length - 1]?.age}</span>
        </div>
        <p className="mt-2 text-[10px] text-apple-gray-400">
          Green bars are millionaire territory. Amounts are in today's dollars, after {INFLATION}% inflation.
        </p>
      </div>

      <Link
        to={`/compass/ask?q=${encodeURIComponent('Look at my retirement plan — what is the single best change I could make?')}`}
        className="animate-fadeUp flex min-h-[48px] items-center justify-center gap-2 rounded-xl border border-apple-gray-200 bg-white text-sm font-medium text-apple-gray-600 active:bg-apple-gray-100"
        style={{ animationDelay: '300ms' }}
      >
        <MessageCircleQuestion size={15} className="text-apple-blue" /> Ask Compass to review my plan
      </Link>
    </div>
  )
}
