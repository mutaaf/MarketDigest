// Compass — Explore: browse the fund database. Filter, search, tap for detail.
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, ArrowLeftRight, ChevronRight } from 'lucide-react'
import api from '../api/client'
import {
  ErrorState, GradeChip, PageSkeleton, Sheet, Skeleton, inputCls,
} from '../components/compass/ui'

interface EtfRow {
  symbol: string
  name: string
  category: string
  asset_class: string
  cached: boolean
  expense_ratio?: number | null
  dividend_yield?: number | null
  return_5y?: number | null
  grade?: string
  overall?: number
  risk_level?: string
}

interface EtfDetail extends EtfRow {
  aum?: number | null
  return_1y?: number | null
  return_10y?: number | null
  volatility_1y?: number | null
  fund_family?: string | null
  scores?: Record<string, number>
  top_holdings?: { symbol: string; name: string; weight: number }[]
  sector_weights?: Record<string, number>
}

const GROUPS: { key: string; label: string; match: (c: string) => boolean }[] = [
  { key: 'all', label: 'All', match: () => true },
  { key: 'us', label: 'US stocks', match: c => c.startsWith('us_') || ['factor', 'low_volatility'].includes(c) },
  { key: 'intl', label: 'International', match: c => c.startsWith('intl_') },
  { key: 'bonds', label: 'Bonds', match: c => c.startsWith('bond_') },
  { key: 'dividend', label: 'Dividend', match: c => ['dividend', 'covered_call'].includes(c) },
  { key: 'sectors', label: 'Sectors', match: c => c.startsWith('sector_') },
  { key: 'reit', label: 'Real estate', match: c => c === 'reit' },
  { key: 'other', label: 'Gold & more', match: c => ['gold', 'commodity', 'thematic'].includes(c) },
]

export default function CompassExplore() {
  const [etfs, setEtfs] = useState<EtfRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [group, setGroup] = useState('all')
  const [query, setQuery] = useState('')
  const [detail, setDetail] = useState<string | null>(null)

  const load = () => {
    setError(null)
    api.get<{ etfs: EtfRow[] }>('/etf/list')
      .then(res => setEtfs(res.data.etfs))
      .catch(err => setError(err.response?.data?.detail || err.message))
  }
  useEffect(load, [])

  const shown = useMemo(() => {
    if (!etfs) return []
    const g = GROUPS.find(x => x.key === group) ?? GROUPS[0]
    const q = query.trim().toUpperCase()
    return etfs
      .filter(e => g.match(e.category))
      .filter(e => !q || e.symbol.includes(q) || e.name.toUpperCase().includes(q))
      .sort((a, b) => (b.overall ?? -1) - (a.overall ?? -1) || a.symbol.localeCompare(b.symbol))
  }, [etfs, group, query])

  if (error) return <ErrorState message={error} onRetry={load} />
  if (!etfs) return <PageSkeleton />

  return (
    <div className="space-y-3 pb-6">
      <div>
        <h1 className="text-lg font-bold text-apple-gray-800">Explore funds</h1>
        <p className="text-xs text-apple-gray-500">
          {etfs.length} funds, graded A–F on safety, growth, income, spread, and cost.
        </p>
      </div>

      <div className="relative">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-apple-gray-300" />
        <input value={query} onChange={e => setQuery(e.target.value)}
          placeholder="Search by ticker or name…"
          className={`${inputCls} pl-9`} />
      </div>

      <div className="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-1" style={{ scrollbarWidth: 'none' }}>
        {GROUPS.map(g => (
          <button key={g.key} onClick={() => setGroup(g.key)}
            className={`shrink-0 rounded-full px-3.5 py-2 text-xs font-medium ${
              group === g.key ? 'bg-apple-blue text-white' : 'border border-apple-gray-200 bg-white text-apple-gray-600'
            }`}>
            {g.label}
          </button>
        ))}
      </div>

      <div className="space-y-1.5">
        {shown.map(e => (
          <button key={e.symbol} onClick={() => setDetail(e.symbol)}
            className="flex w-full items-center justify-between gap-3 rounded-2xl border border-apple-gray-200 bg-white px-4 py-3 text-left active:bg-apple-gray-50">
            <div className="min-w-0">
              <p className="font-semibold text-apple-gray-800">{e.symbol}</p>
              <p className="truncate text-xs text-apple-gray-500">{e.name}</p>
              {e.cached && (
                <p className="mt-0.5 text-[11px] tabular-nums text-apple-gray-400">
                  {e.expense_ratio != null && `${e.expense_ratio.toFixed(2)}%/yr`}
                  {e.return_5y != null && ` · ${e.return_5y.toFixed(1)}%/yr over 5y`}
                  {e.dividend_yield != null && ` · yields ${e.dividend_yield.toFixed(1)}%`}
                </p>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {e.grade
                ? <GradeChip grade={e.grade} />
                : <span className="text-[10px] text-apple-gray-300">tap to analyze</span>}
              <ChevronRight size={15} className="text-apple-gray-300" />
            </div>
          </button>
        ))}
        {shown.length === 0 && (
          <p className="py-8 text-center text-sm text-apple-gray-400">No funds match that search.</p>
        )}
      </div>

      {detail && <EtfDetailSheet symbol={detail} onClose={() => { setDetail(null); load() }} />}
    </div>
  )
}

function EtfDetailSheet({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  const [data, setData] = useState<EtfDetail | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.get<EtfDetail>(`/etf/${symbol}`, { timeout: 60000 })
      .then(res => setData(res.data))
      .catch(e => setErr(e.response?.data?.detail || e.message))
  }, [symbol])

  const fmtAum = (v?: number | null) =>
    v == null ? '—' : v >= 1e12 ? `$${(v / 1e12).toFixed(1)}T` : v >= 1e9 ? `$${(v / 1e9).toFixed(0)}B` : `$${(v / 1e6).toFixed(0)}M`

  return (
    <Sheet title={symbol} onClose={onClose}>
      {err && <p className="text-sm text-apple-red">{err}</p>}
      {!data && !err && (
        <div className="space-y-2">
          <p className="text-xs text-apple-gray-400">Analyzing {symbol} — a few seconds on first look…</p>
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}
      {data && (
        <div className="max-h-[70vh] space-y-4 overflow-y-auto">
          <div className="flex items-center gap-3">
            <GradeChip grade={data.grade} size="lg" />
            <div>
              <p className="text-sm font-semibold text-apple-gray-800">{data.name}</p>
              <p className="text-xs text-apple-gray-400">
                {data.fund_family}{data.risk_level ? ` · ${data.risk_level} risk` : ''} · {fmtAum(data.aum)} fund
              </p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center">
            <MiniStat label="Cost / yr" value={data.expense_ratio != null ? `${data.expense_ratio.toFixed(2)}%` : '—'} />
            <MiniStat label="Yield" value={data.dividend_yield != null ? `${data.dividend_yield.toFixed(1)}%` : '—'} />
            <MiniStat label="5y return" value={data.return_5y != null ? `${data.return_5y.toFixed(1)}%/yr` : '—'} />
          </div>

          {data.scores && (
            <div className="space-y-1.5">
              {Object.entries(data.scores).map(([k, v]) => (
                <div key={k}>
                  <div className="mb-0.5 flex justify-between text-xs">
                    <span className="capitalize text-apple-gray-600">{k}</span>
                    <span className="tabular-nums text-apple-gray-400">{v.toFixed(0)}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-apple-gray-100">
                    <div className="h-full rounded-full bg-apple-blue" style={{ width: `${v}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {(data.top_holdings?.length ?? 0) > 0 && (
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-apple-gray-400">Biggest holdings</p>
              {data.top_holdings!.slice(0, 5).map(h => (
                <div key={h.symbol} className="flex justify-between py-0.5 text-xs text-apple-gray-600">
                  <span className="truncate">{h.symbol} <span className="text-apple-gray-400">{h.name}</span></span>
                  <span className="tabular-nums">{h.weight.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          )}

          <Link to={`/compass/compare?a=${symbol}`}
            className="flex min-h-[48px] items-center justify-center gap-2 rounded-xl border border-apple-blue/30 bg-apple-blue/5 text-sm font-semibold text-apple-blue active:bg-apple-blue/10">
            <ArrowLeftRight size={15} /> Compare {symbol} with something
          </Link>
        </div>
      )}
    </Sheet>
  )
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-apple-gray-50 py-2">
      <p className="text-[10px] font-medium uppercase tracking-wide text-apple-gray-400">{label}</p>
      <p className="text-sm font-semibold tabular-nums text-apple-gray-800">{value}</p>
    </div>
  )
}
