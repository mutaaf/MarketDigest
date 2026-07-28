// Compass — Compare any two ETFs or stocks side by side.
import { FormEvent, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ArrowLeftRight } from 'lucide-react'
import api from '../api/client'
import { CompareResult, CompareSide, SearchResult } from '../api/compass-types'
import { ErrorState, GradeChip, Skeleton } from '../components/compass/ui'

const METRIC_LABELS: Record<string, { label: string; suffix?: string; lowerBetter?: boolean }> = {
  expense_ratio: { label: 'Yearly cost (expense ratio)', suffix: '%', lowerBetter: true },
  dividend_yield: { label: 'Dividend yield', suffix: '%' },
  return_1y: { label: 'Return, last 1 year', suffix: '%/yr' },
  return_5y: { label: 'Return, last 5 years', suffix: '%/yr' },
  return_10y: { label: 'Return, last 10 years', suffix: '%/yr' },
  volatility_1y: { label: 'Choppiness (volatility)', suffix: '%', lowerBetter: true },
  aum: { label: 'Fund size' },
  pe_ratio: { label: 'Price vs earnings (P/E)', lowerBetter: true },
  forward_pe: { label: 'Forward P/E', lowerBetter: true },
  peg_ratio: { label: 'PEG ratio', lowerBetter: true },
  revenue_growth: { label: 'Revenue growth', suffix: '%' },
  net_margin: { label: 'Profit margin', suffix: '%' },
  debt_equity: { label: 'Debt vs equity', lowerBetter: true },
  current_price: { label: 'Current price', suffix: ' $' },
  analyst_target: { label: 'Analyst avg target', suffix: ' $' },
  market_cap: { label: 'Company size' },
}

function fmt(key: string, v: number | null): string {
  if (v === null || v === undefined) return '—'
  if (key === 'aum' || key === 'market_cap') {
    if (v >= 1e12) return `$${(v / 1e12).toFixed(1)}T`
    if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`
    return `$${(v / 1e6).toFixed(0)}M`
  }
  const suffix = METRIC_LABELS[key]?.suffix ?? ''
  return `${v.toLocaleString('en-US', { maximumFractionDigits: 2 })}${suffix}`
}

export default function CompassCompare() {
  const [params] = useSearchParams()
  const [a, setA] = useState(params.get('a')?.toUpperCase() || 'VOO')
  const [b, setB] = useState(params.get('b')?.toUpperCase() || 'VTI')
  const [result, setResult] = useState<CompareResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async (e?: FormEvent) => {
    e?.preventDefault()
    if (!a.trim() || !b.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.get<CompareResult>('/compass/compare', {
        params: { a: a.trim(), b: b.trim() }, timeout: 120000,
      })
      setResult(res.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const metricKeys = result
    ? Object.keys(METRIC_LABELS).filter(k =>
        result.a.metrics[k] !== undefined || result.b.metrics[k] !== undefined)
    : []

  return (
    <div className="mx-auto max-w-3xl space-y-4 pb-6">
      <form onSubmit={run} className="flex items-end gap-2">
        <SymbolInput label="First" value={a} onChange={setA} />
        <div className="flex min-h-[44px] items-center text-apple-gray-300"><ArrowLeftRight size={18} /></div>
        <SymbolInput label="Second" value={b} onChange={setB} />
        <button type="submit" disabled={loading}
          className="min-h-[44px] rounded-xl bg-apple-blue px-5 text-sm font-semibold text-white active:opacity-80 disabled:opacity-40">
          {loading ? '…' : 'Compare'}
        </button>
      </form>
      <p className="text-xs text-apple-gray-400">Works with any fund or stock — try VOO vs VTI, or MSFT vs META.</p>

      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}
      {error && <ErrorState message={error} onRetry={() => run()} />}

      {result && !loading && (
        <>
          {/* Header cards */}
          <div className="grid grid-cols-2 gap-3">
            {[result.a, result.b].map(side => (
              <div key={side.symbol} className="rounded-2xl border border-apple-gray-200 bg-white p-4 text-center">
                <GradeChip grade={side.grade} />
                <p className="mt-2 text-lg font-bold text-apple-gray-800">{side.symbol}</p>
                <p className="text-xs leading-tight text-apple-gray-500">{side.name}</p>
                <p className="mt-1 text-[11px] uppercase tracking-wide text-apple-gray-400">
                  {side.type === 'etf' ? 'Fund' : side.sector || 'Stock'}
                  {side.risk_level ? ` · ${side.risk_level} risk` : ''}
                </p>
              </div>
            ))}
          </div>

          {/* Verdict */}
          <div className="rounded-2xl bg-apple-blue/5 p-4">
            <p className="text-sm leading-relaxed text-apple-gray-700">{result.verdict}</p>
          </div>

          {/* Metric table */}
          <div className="overflow-hidden rounded-2xl border border-apple-gray-200 bg-white">
            {metricKeys.map((key, i) => {
              const va = result.a.metrics[key] ?? null
              const vb = result.b.metrics[key] ?? null
              const winner = highlight(key, va, vb)
              return (
                <div key={key} className={`grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-4 py-2.5 ${i % 2 ? 'bg-apple-gray-50/60' : ''}`}>
                  <span className={`text-sm tabular-nums ${winner === 'a' ? 'font-semibold text-apple-gray-800' : 'text-apple-gray-500'}`}>
                    {fmt(key, va)}
                  </span>
                  <span className="text-center text-[11px] leading-tight text-apple-gray-400">{METRIC_LABELS[key].label}</span>
                  <span className={`text-right text-sm tabular-nums ${winner === 'b' ? 'font-semibold text-apple-gray-800' : 'text-apple-gray-500'}`}>
                    {fmt(key, vb)}
                  </span>
                </div>
              )
            })}
          </div>

          {/* Sub-scores */}
          <div className="grid grid-cols-2 gap-3">
            {[result.a, result.b].map(side => <SubScores key={side.symbol} side={side} />)}
          </div>
        </>
      )}
    </div>
  )
}

function highlight(key: string, a: number | null, b: number | null): 'a' | 'b' | null {
  if (a === null || b === null || a === b) return null
  if (key === 'current_price' || key === 'analyst_target') return null
  const lowerBetter = METRIC_LABELS[key]?.lowerBetter ?? false
  return (a < b) === lowerBetter ? 'a' : 'b'
}

function SubScores({ side }: { side: CompareSide }) {
  const entries = Object.entries(side.sub_scores).filter(([, v]) => v !== null) as [string, number][]
  if (!entries.length) return <div />
  return (
    <div className="rounded-2xl border border-apple-gray-200 bg-white p-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-apple-gray-400">{side.symbol} scores</p>
      <div className="space-y-2">
        {entries.map(([k, v]) => (
          <div key={k}>
            <div className="mb-0.5 flex justify-between text-xs">
              <span className="capitalize text-apple-gray-600">{k}</span>
              <span className="tabular-nums text-apple-gray-500">{v.toFixed(0)}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-apple-gray-100">
              <div className="h-full rounded-full bg-apple-blue" style={{ width: `${v}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function SymbolInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const timer = useRef<number>()

  const handle = (v: string) => {
    onChange(v.toUpperCase())
    window.clearTimeout(timer.current)
    if (!v.trim()) { setSuggestions([]); return }
    timer.current = window.setTimeout(() => {
      api.get<{ results: SearchResult[] }>('/compass/search', { params: { q: v } })
        .then(res => setSuggestions(res.data.results.slice(0, 5)))
        .catch(() => setSuggestions([]))
    }, 200)
  }

  return (
    <div className="relative flex-1">
      <label className="mb-1 block text-xs font-medium text-apple-gray-500">{label}</label>
      <input value={value} onChange={e => handle(e.target.value)} autoCapitalize="characters" autoCorrect="off"
        className="w-full min-h-[44px] rounded-xl border border-apple-gray-200 bg-white px-3 text-sm font-medium text-apple-gray-800 focus:border-apple-blue focus:outline-none" />
      {suggestions.length > 0 && (
        <div className="absolute z-10 mt-1 w-full min-w-[14rem] overflow-hidden rounded-xl border border-apple-gray-200 bg-white shadow-lg">
          {suggestions.map(s => (
            <button key={s.symbol} type="button"
              onClick={() => { onChange(s.symbol); setSuggestions([]) }}
              className="flex w-full items-center justify-between px-3 py-2.5 text-left text-sm active:bg-apple-gray-50">
              <span className="font-medium">{s.symbol}</span>
              <span className="ml-2 truncate text-xs text-apple-gray-400">{s.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
