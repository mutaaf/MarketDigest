// Compass — Welcome: guided first-run setup. Three friendly steps:
// who it's for → what you own → how you want it split. Mobile-first.
import { FormEvent, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Compass, Plus, Check, Upload, Trash2 } from 'lucide-react'
import api from '../api/client'
import { SearchResult } from '../api/compass-types'
import { inputCls, primaryBtn } from '../components/compass/ui'
import SmartImport from '../components/compass/SmartImport'

type Step = 'name' | 'holdings' | 'targets' | 'done'

interface DraftHolding {
  symbol: string
  shares: number
  cost: number
}

const PRESETS = [
  {
    key: 'balanced', label: 'Balanced', tag: 'Recommended',
    blurb: 'Mostly stocks for growth, with bonds and real estate to steady the ride.',
    targets: { us_stock: 55, intl_stock: 20, bond: 15, reit: 5, cash: 5 },
  },
  {
    key: 'growth', label: 'Growth', tag: 'For long horizons',
    blurb: 'Nearly all stocks. Bigger swings, historically bigger long-term growth.',
    targets: { us_stock: 70, intl_stock: 20, bond: 0, reit: 5, cash: 5 },
  },
  {
    key: 'careful', label: 'Careful', tag: 'Smoother ride',
    blurb: 'More bonds, fewer swings. Grows slower but sleeps better.',
    targets: { us_stock: 40, intl_stock: 15, bond: 35, reit: 5, cash: 5 },
  },
]

export default function CompassWelcome() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('name')
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [holdings, setHoldings] = useState<DraftHolding[]>([])
  const [cash, setCash] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const stepIndex = { name: 0, holdings: 1, targets: 2, done: 3 }[step]

  const createPortfolio = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setErr(null)
    try {
      const res = await api.post('/portfolio/create', { name: name.trim() }, { timeout: 15000 })
      const s = res.data.slug as string
      setSlug(s)
      localStorage.setItem('compass.selectedPortfolio', s)
      setStep('holdings')
    } catch (error: any) {
      const detail = error.response?.data?.detail
      setErr(detail || "Couldn't reach Compass just now — give it a few seconds and tap Continue again.")
    } finally {
      setBusy(false)
    }
  }

  const finishHoldings = async () => {
    setBusy(true)
    setErr(null)
    try {
      if (cash.trim() && parseFloat(cash) > 0) {
        await api.put(`/portfolio/${slug}/cash`, { amount: parseFloat(cash) })
      }
      setStep('targets')
    } catch {
      setErr("Couldn't save the cash amount — you can set it later on the Portfolio page.")
      setStep('targets')
    } finally {
      setBusy(false)
    }
  }

  const pickPreset = async (targets: Record<string, number> | null) => {
    setBusy(true)
    setErr(null)
    try {
      if (targets) await api.put(`/portfolio/${slug}/targets`, { targets })
      setStep('done')
      setTimeout(() => navigate('/compass'), 1600)
    } catch {
      setStep('done')
      setTimeout(() => navigate('/compass'), 1600)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md">
      {/* Progress dots */}
      {step !== 'done' && (
        <div className="mb-6 flex items-center justify-center gap-2">
          {[0, 1, 2].map(i => (
            <div key={i} className={`h-1.5 rounded-full transition-all ${i === stepIndex ? 'w-8 bg-apple-blue' : i < stepIndex ? 'w-4 bg-apple-blue/40' : 'w-4 bg-apple-gray-200'}`} />
          ))}
        </div>
      )}

      {step === 'name' && (
        <form onSubmit={createPortfolio} className="space-y-4 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-apple-blue/10">
            <Compass size={26} className="text-apple-blue" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-apple-gray-800">Welcome to Compass</h1>
            <p className="mx-auto mt-1 max-w-xs text-sm text-apple-gray-500">
              Three quick steps and you'll see how your investments are doing — and what to buy next.
            </p>
          </div>
          <div className="text-left">
            <label className="mb-1 block text-xs font-medium text-apple-gray-500">Whose money is this?</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Sarah" autoFocus className={inputCls} />
          </div>
          {err && <p className="text-xs text-apple-red">{err}</p>}
          <button type="submit" disabled={busy || !name.trim()} className={primaryBtn}>
            {busy ? 'Creating…' : 'Continue'}
          </button>
        </form>
      )}

      {step === 'holdings' && (
        <HoldingsStep
          slug={slug}
          holdings={holdings}
          setHoldings={setHoldings}
          cash={cash}
          setCash={setCash}
          busy={busy}
          err={err}
          onContinue={finishHoldings}
        />
      )}

      {step === 'targets' && (
        <div className="space-y-4">
          <div className="text-center">
            <h1 className="text-xl font-bold text-apple-gray-800">How should your money be split?</h1>
            <p className="mx-auto mt-1 max-w-xs text-sm text-apple-gray-500">
              This becomes your plan — Compass compares what you own against it and suggests what to buy. You can change it anytime.
            </p>
          </div>
          {PRESETS.map(p => (
            <button key={p.key} onClick={() => pickPreset(p.targets)} disabled={busy}
              className="w-full rounded-2xl border border-apple-gray-200 bg-white p-4 text-left active:bg-apple-gray-50 disabled:opacity-50">
              <div className="flex items-center justify-between">
                <p className="text-base font-semibold text-apple-gray-800">{p.label}</p>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${p.key === 'balanced' ? 'bg-apple-blue/10 text-apple-blue' : 'bg-apple-gray-100 text-apple-gray-500'}`}>
                  {p.tag}
                </span>
              </div>
              <p className="mt-1 text-sm text-apple-gray-500">{p.blurb}</p>
              <div className="mt-3 flex h-2 overflow-hidden rounded-full">
                <div className="bg-apple-blue" style={{ width: `${p.targets.us_stock}%` }} title="US stocks" />
                <div className="bg-sky-400" style={{ width: `${p.targets.intl_stock}%` }} title="International" />
                <div className="bg-apple-gray-300" style={{ width: `${p.targets.bond}%` }} title="Bonds" />
                <div className="bg-emerald-400" style={{ width: `${p.targets.reit}%` }} title="Real estate" />
                <div className="bg-apple-yellow" style={{ width: `${p.targets.cash}%` }} title="Cash" />
              </div>
              <p className="mt-1.5 text-[10px] text-apple-gray-400">
                {p.targets.us_stock}% US · {p.targets.intl_stock}% intl · {p.targets.bond}% bonds · {p.targets.reit}% real estate · {p.targets.cash}% cash
              </p>
            </button>
          ))}
          <button onClick={() => pickPreset(null)} disabled={busy}
            className="w-full py-2 text-center text-sm text-apple-gray-400 active:text-apple-gray-600">
            Skip — decide later
          </button>
        </div>
      )}

      {step === 'done' && (
        <div className="flex flex-col items-center pt-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-apple-green/15">
            <Check size={30} className="text-green-600" />
          </div>
          <h1 className="mt-4 text-xl font-bold text-apple-gray-800">You're all set{name ? `, ${name}` : ''}!</h1>
          <p className="mt-1 text-sm text-apple-gray-500">Taking you to your home screen…</p>
        </div>
      )}
    </div>
  )
}

function HoldingsStep({ slug, holdings, setHoldings, cash, setCash, busy, err, onContinue }: {
  slug: string
  holdings: DraftHolding[]
  setHoldings: (h: DraftHolding[]) => void
  cash: string
  setCash: (v: string) => void
  busy: boolean
  err: string | null
  onContinue: () => void
}) {
  const [symbol, setSymbol] = useState('')
  const [shares, setShares] = useState('')
  const [cost, setCost] = useState('')
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const [adding, setAdding] = useState(false)
  const [rowErr, setRowErr] = useState<string | null>(null)
  const [showImport, setShowImport] = useState(false)
  const timer = useRef<number>()

  const onSymbolChange = (val: string) => {
    setSymbol(val.toUpperCase())
    window.clearTimeout(timer.current)
    if (!val.trim()) { setSuggestions([]); return }
    timer.current = window.setTimeout(() => {
      api.get<{ results: SearchResult[] }>('/compass/search', { params: { q: val } })
        .then(res => setSuggestions(res.data.results.slice(0, 4)))
        .catch(() => setSuggestions([]))
    }, 200)
  }

  const addRow = async () => {
    const sh = parseFloat(shares)
    if (!symbol.trim() || !sh || sh <= 0) return
    setAdding(true)
    setRowErr(null)
    try {
      await api.post(`/portfolio/${slug}/holding`, {
        symbol: symbol.trim(), shares: sh, cost_basis: cost ? parseFloat(cost) : 0,
      })
      setHoldings([...holdings, { symbol: symbol.trim(), shares: sh, cost: cost ? parseFloat(cost) : 0 }])
      setSymbol(''); setShares(''); setCost(''); setSuggestions([])
    } catch (error: any) {
      setRowErr(error.response?.data?.detail || "Couldn't add that one — check the ticker.")
    } finally {
      setAdding(false)
    }
  }

  const removeRow = async (sym: string) => {
    try {
      await api.delete(`/portfolio/${slug}/holding/${sym}`)
      setHoldings(holdings.filter(h => h.symbol !== sym))
    } catch { /* row stays; harmless */ }
  }

  const refreshFromServer = async () => {
    const summary = await api.get(`/portfolio/${slug}/summary`)
    setHoldings(summary.data.valuation.holdings.map((h: any) => ({ symbol: h.symbol, shares: h.shares, cost: h.cost_basis })))
    setShowImport(false)
  }

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h1 className="text-xl font-bold text-apple-gray-800">What do you own?</h1>
        <p className="mx-auto mt-1 max-w-xs text-sm text-apple-gray-500">
          Add each investment — the ticker, how many shares, and (if you remember) what you paid. Rough is fine.
        </p>
      </div>

      {holdings.length > 0 && (
        <div className="space-y-1.5">
          {holdings.map(h => (
            <div key={h.symbol} className="flex items-center justify-between rounded-xl border border-apple-gray-200 bg-white px-3 py-2">
              <p className="text-sm font-semibold text-apple-gray-800">{h.symbol}
                <span className="ml-2 text-xs font-normal text-apple-gray-400">{h.shares} shares{h.cost ? ` @ $${h.cost}` : ''}</span>
              </p>
              <button onClick={() => removeRow(h.symbol)} className="flex min-h-[36px] min-w-[36px] items-center justify-center text-apple-gray-300 active:text-apple-red">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {!showImport ? (
        <div className="rounded-2xl border border-apple-gray-200 bg-white p-3">
          <div className="relative">
            <input value={symbol} onChange={e => onSymbolChange(e.target.value)} placeholder="Ticker — e.g. VOO"
              autoCapitalize="characters" autoCorrect="off" className={inputCls} />
            {suggestions.length > 0 && (
              <div className="absolute z-10 mt-1 w-full overflow-hidden rounded-xl border border-apple-gray-200 bg-white shadow-lg">
                {suggestions.map(s => (
                  <button key={s.symbol} type="button" onClick={() => { setSymbol(s.symbol); setSuggestions([]) }}
                    className="flex w-full items-center justify-between px-3 py-2.5 text-left text-sm active:bg-apple-gray-50">
                    <span className="font-medium">{s.symbol}</span>
                    <span className="ml-2 truncate text-xs text-apple-gray-400">{s.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <input value={shares} onChange={e => setShares(e.target.value)} placeholder="Shares" inputMode="decimal" className={inputCls} />
            <input value={cost} onChange={e => setCost(e.target.value)} placeholder="Paid per share (opt.)" inputMode="decimal" className={inputCls} />
          </div>
          {rowErr && <p className="mt-2 text-xs text-apple-red">{rowErr}</p>}
          <button onClick={addRow} disabled={adding || !symbol.trim() || !parseFloat(shares)}
            className="mt-2 flex min-h-[44px] w-full items-center justify-center gap-1.5 rounded-xl border border-apple-blue/30 bg-apple-blue/5 text-sm font-semibold text-apple-blue active:bg-apple-blue/10 disabled:opacity-40">
            <Plus size={15} /> {adding ? 'Adding…' : 'Add this holding'}
          </button>
          <button onClick={() => setShowImport(true)} className="mt-1 flex min-h-[36px] w-full items-center justify-center gap-1.5 text-xs text-apple-gray-400 active:text-apple-gray-600">
            <Upload size={12} /> Or import from a screenshot, pasted text, or CSV
          </button>
        </div>
      ) : (
        <div className="rounded-2xl border border-apple-gray-200 bg-white p-3">
          <SmartImport slug={slug} onDone={refreshFromServer} />
          <button onClick={() => setShowImport(false)}
            className="mt-2 flex min-h-[36px] w-full items-center justify-center text-xs text-apple-gray-400 active:text-apple-gray-600">
            Back to typing them in
          </button>
        </div>
      )}

      <div>
        <label className="mb-1 block text-xs font-medium text-apple-gray-500">Cash waiting to be invested <span className="text-apple-gray-300">(optional)</span></label>
        <input value={cash} onChange={e => setCash(e.target.value)} placeholder="5000" inputMode="decimal" className={inputCls} />
      </div>

      {err && <p className="text-xs text-apple-red">{err}</p>}
      <button onClick={onContinue} disabled={busy} className={primaryBtn}>
        {busy ? 'Saving…' : holdings.length ? 'Continue' : 'Skip for now — continue'}
      </button>
    </div>
  )
}
