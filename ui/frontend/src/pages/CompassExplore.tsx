// Compass — Explore: browse the fund database. Filter, search, tap for detail.
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, ArrowLeftRight, ChevronRight, MessageCircleQuestion, Plus, Check, Eye } from 'lucide-react'
import api from '../api/client'
import {
  ErrorState, GradeChip, MoneyInput, PageSkeleton, Sheet, Skeleton, inputCls,
  usePortfolioSelection,
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

interface StockRow {
  symbol: string
  name: string
  sector: string | null
  cached: boolean
  grade?: string
  overall?: number
  pe_ratio?: number | null
  dividend_yield?: number | null
  revenue_growth?: number | null
}

interface CryptoRow {
  symbol: string
  name: string
  price: number | null
  return_1y: number | null
  return_5y: number | null
  volatility_1y: number | null
}

export default function CompassExplore() {
  const [kind, setKind] = useState<'funds' | 'stocks' | 'crypto'>('funds')
  const [etfs, setEtfs] = useState<EtfRow[] | null>(null)
  const [stocks, setStocks] = useState<StockRow[] | null>(null)
  const [cryptos, setCryptos] = useState<CryptoRow[] | null>(null)
  const [openCrypto, setOpenCrypto] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [group, setGroup] = useState('all')
  const [sector, setSector] = useState('All')
  const [query, setQuery] = useState('')
  const [detail, setDetail] = useState<string | null>(null)
  const [stockDetail, setStockDetail] = useState<string | null>(null)

  const load = () => {
    setError(null)
    api.get<{ etfs: EtfRow[] }>('/etf/list')
      .then(res => setEtfs(res.data.etfs))
      .catch(err => setError(err.response?.data?.detail || err.message))
    api.get<{ stocks: StockRow[] }>('/compass/stocks')
      .then(res => setStocks(res.data.stocks))
      .catch(() => setStocks([]))
    api.get<{ cryptos: CryptoRow[] }>('/compass/cryptos', { timeout: 90000 })
      .then(res => setCryptos(res.data.cryptos))
      .catch(() => setCryptos([]))
  }
  useEffect(load, [])

  const sectors = useMemo(() => {
    const s = new Set<string>()
    for (const st of stocks ?? []) if (st.sector) s.add(st.sector)
    return ['All', ...[...s].sort()]
  }, [stocks])

  const shownStocks = useMemo(() => {
    if (!stocks) return []
    const q = query.trim().toUpperCase()
    return stocks
      .filter(s => sector === 'All' || s.sector === sector)
      .filter(s => !q || s.symbol.includes(q) || (s.name || '').toUpperCase().includes(q))
      .sort((a, b) => (b.overall ?? -1) - (a.overall ?? -1) || a.symbol.localeCompare(b.symbol))
  }, [stocks, sector, query])

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
        <h1 className="text-lg font-bold text-apple-gray-800">Explore</h1>
        <p className="text-xs text-apple-gray-500">
          {etfs.length} funds and {stocks?.length ?? '…'} companies, graded A–F.
        </p>
      </div>

      {/* Funds | Stocks | Crypto toggle */}
      <div className="grid grid-cols-3 gap-1 rounded-xl bg-apple-gray-200/60 p-1">
        {(['funds', 'stocks', 'crypto'] as const).map(k => (
          <button key={k} onClick={() => setKind(k)}
            className={`min-h-[40px] rounded-lg text-sm font-semibold capitalize transition-colors ${
              kind === k ? 'bg-white text-apple-gray-800 shadow-sm' : 'text-apple-gray-500'
            }`}>
            {k}
          </button>
        ))}
      </div>

      <div className="relative">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-apple-gray-300" />
        <input value={query} onChange={e => setQuery(e.target.value)}
          placeholder="Search by ticker or name…"
          className={`${inputCls} pl-9`} />
      </div>

      <div className="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-1" style={{ scrollbarWidth: 'none' }}>
        {kind === 'funds' ? GROUPS.map(g => (
          <button key={g.key} onClick={() => setGroup(g.key)}
            className={`shrink-0 rounded-full px-3.5 py-2 text-xs font-medium ${
              group === g.key ? 'bg-apple-blue text-white' : 'border border-apple-gray-200 bg-white text-apple-gray-600'
            }`}>
            {g.label}
          </button>
        )) : sectors.map(s => (
          <button key={s} onClick={() => setSector(s)}
            className={`shrink-0 rounded-full px-3.5 py-2 text-xs font-medium ${
              sector === s ? 'bg-apple-blue text-white' : 'border border-apple-gray-200 bg-white text-apple-gray-600'
            }`}>
            {s}
          </button>
        ))}
      </div>

      {kind === 'crypto' && (
        <div className="space-y-1.5">
          <p className="rounded-xl bg-apple-yellow/10 px-3 py-2 text-[11px] leading-relaxed text-yellow-800">
            Crypto is the most volatile thing in Compass — no letter grades here, just honest
            numbers. A common guideline keeps it under ~5% of a portfolio.
          </p>
          {cryptos === null && <PageSkeleton />}
          {cryptos?.map(c => (
            <div key={c.symbol} className="rounded-2xl border border-apple-gray-200 bg-white">
              <button onClick={() => setOpenCrypto(openCrypto === c.symbol ? null : c.symbol)}
                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left active:bg-apple-gray-50">
                <div>
                  <p className="font-semibold text-apple-gray-800">{c.symbol} <span className="text-xs font-normal text-apple-gray-400">{c.name}</span></p>
                  <p className="mt-0.5 text-[11px] tabular-nums text-apple-gray-400">
                    {c.price != null && `$${c.price.toLocaleString('en-US', { maximumFractionDigits: c.price > 10 ? 0 : 4 })}`}
                    {c.return_1y != null && ` · ${c.return_1y > 0 ? '+' : ''}${c.return_1y.toFixed(0)}% past year`}
                    {c.volatility_1y != null && ` · ${c.volatility_1y.toFixed(0)}% volatility`}
                  </p>
                </div>
                <ChevronRight size={15} className={`text-apple-gray-300 transition-transform ${openCrypto === c.symbol ? 'rotate-90' : ''}`} />
              </button>
              {openCrypto === c.symbol && (
                <div className="animate-fadeUp grid grid-cols-2 gap-2 border-t border-apple-gray-100 p-3">
                  <Link to={`/compass/compare?a=${c.symbol}&b=VOO`}
                    className="flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-apple-gray-200 bg-white text-xs font-semibold text-apple-gray-700 active:bg-apple-gray-100">
                    <ArrowLeftRight size={13} /> vs VOO
                  </Link>
                  <Link to={`/compass/ask?q=${encodeURIComponent(`Should ${c.name} (${c.symbol}) be part of my portfolio?`)}`}
                    className="flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-apple-gray-200 bg-white text-xs font-semibold text-apple-gray-700 active:bg-apple-gray-100">
                    <MessageCircleQuestion size={13} /> Ask Compass
                  </Link>
                </div>
              )}
            </div>
          ))}
          <p className="text-[10px] text-apple-gray-400">
            Own some already? Add it from the Portfolio page — it tracks like everything else.
          </p>
        </div>
      )}

      {kind === 'stocks' && (
        <div className="space-y-1.5">
          {shownStocks.map(s => (
            <button key={s.symbol} onClick={() => setStockDetail(s.symbol)}
              className="flex w-full items-center justify-between gap-3 rounded-2xl border border-apple-gray-200 bg-white px-4 py-3 text-left active:bg-apple-gray-50">
              <div className="min-w-0">
                <p className="font-semibold text-apple-gray-800">{s.symbol}</p>
                <p className="truncate text-xs text-apple-gray-500">{s.name}{s.sector ? ` · ${s.sector}` : ''}</p>
                {s.cached && (
                  <p className="mt-0.5 text-[11px] tabular-nums text-apple-gray-400">
                    {s.pe_ratio != null && `P/E ${s.pe_ratio.toFixed(0)}`}
                    {s.revenue_growth != null && ` · growing ${s.revenue_growth.toFixed(0)}%/yr`}
                    {s.dividend_yield != null && s.dividend_yield > 0.1 && ` · yields ${s.dividend_yield.toFixed(1)}%`}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {s.grade
                  ? <GradeChip grade={s.grade} />
                  : <span className="text-[10px] text-apple-gray-300">tap to analyze</span>}
                <ChevronRight size={15} className="text-apple-gray-300" />
              </div>
            </button>
          ))}
          {shownStocks.length === 0 && (
            <p className="py-8 text-center text-sm text-apple-gray-400">No companies match that search.</p>
          )}
        </div>
      )}

      {kind === 'funds' && <div className="space-y-1.5">
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
      </div>}

      {detail && <EtfDetailSheet symbol={detail} onClose={() => { setDetail(null); load() }} />}
      {stockDetail && <StockDetailSheet symbol={stockDetail} onClose={() => { setStockDetail(null); load() }} />}
    </div>
  )
}

interface StockDetail {
  symbol: string
  name: string
  grade: string
  score: number
  sector?: string
  sub_scores: Record<string, number | null>
  metrics: Record<string, number | null>
}

function StockDetailSheet({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  const { selected } = usePortfolioSelection()
  const [data, setData] = useState<StockDetail | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [buying, setBuying] = useState(false)
  const [shares, setShares] = useState('')
  const [cost, setCost] = useState('')
  const [addState, setAddState] = useState<'idle' | 'saving' | 'done'>('idle')
  const [watchState, setWatchState] = useState<'idle' | 'done'>('idle')

  useEffect(() => {
    api.get<StockDetail>(`/compass/stock/${symbol}`, { timeout: 60000 })
      .then(res => setData(res.data))
      .catch(e => setErr(e.response?.data?.detail || e.message))
  }, [symbol])

  const addToPortfolio = async () => {
    if (!selected || !parseFloat(shares)) return
    setAddState('saving')
    try {
      await api.post(`/portfolio/${selected}/holding`, {
        symbol, shares: parseFloat(shares), cost_basis: cost ? parseFloat(cost) : 0,
      })
      setAddState('done')
    } catch {
      setAddState('idle')
    }
  }

  const watch = async () => {
    if (!selected) return
    try {
      await api.post(`/portfolio/${selected}/watchlist`, { symbol })
      setWatchState('done')
    } catch { /* non-fatal */ }
  }

  const m = data?.metrics ?? {}
  const stat = (v: number | null | undefined, suffix = '', digits = 1) =>
    v == null ? '—' : `${v.toFixed(digits)}${suffix}`

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
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <GradeChip grade={data.grade} size="lg" />
            <div>
              <p className="text-sm font-semibold text-apple-gray-800">{data.name}</p>
              <p className="text-xs text-apple-gray-400">{data.sector || 'Stock'} · quality score {data.score.toFixed(0)}/100</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center">
            <MiniStat label="P/E" value={stat(m.pe_ratio, '', 0)} />
            <MiniStat label="Growth" value={stat(m.revenue_growth, '%/yr', 0)} />
            <MiniStat label="Yield" value={stat(m.dividend_yield, '%')} />
          </div>

          {m.analyst_target != null && m.current_price != null && m.current_price > 0 && (
            <p className="rounded-xl bg-apple-gray-50 p-3 text-xs leading-relaxed text-apple-gray-600">
              Trading at <strong>${m.current_price.toFixed(2)}</strong>; analysts' average target is{' '}
              <strong>${m.analyst_target.toFixed(2)}</strong>{' '}
              ({m.analyst_target > m.current_price ? '+' : ''}{((m.analyst_target / m.current_price - 1) * 100).toFixed(0)}%).
              Targets are opinions, not promises.
            </p>
          )}

          {data.sub_scores && (
            <div className="space-y-1.5">
              {Object.entries(data.sub_scores).filter(([, v]) => v !== null).map(([k, v]) => (
                <div key={k}>
                  <div className="mb-0.5 flex justify-between text-xs">
                    <span className="capitalize text-apple-gray-600">{k}</span>
                    <span className="tabular-nums text-apple-gray-400">{(v as number).toFixed(0)}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-apple-gray-100">
                    <div className="h-full rounded-full bg-apple-blue" style={{ width: `${v}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {addState === 'done' ? (
            <div className="flex min-h-[48px] items-center justify-center gap-2 rounded-xl bg-apple-green/10 text-sm font-semibold text-green-700">
              <Check size={15} /> Added to your portfolio
            </div>
          ) : buying ? (
            <div className="space-y-2 rounded-xl border border-apple-blue/30 bg-apple-blue/5 p-3">
              <div className="grid grid-cols-2 gap-2">
                <input value={shares} onChange={e => setShares(e.target.value)} placeholder="Shares"
                  inputMode="decimal" autoFocus className={inputCls} />
                <MoneyInput value={cost} onChange={setCost} placeholder="Paid each (opt.)" />
              </div>
              <button onClick={addToPortfolio} disabled={addState === 'saving' || !parseFloat(shares)}
                className="flex min-h-[44px] w-full items-center justify-center rounded-xl bg-apple-blue text-sm font-semibold text-white active:opacity-80 disabled:opacity-40">
                {addState === 'saving' ? 'Adding…' : `Add ${symbol} to my portfolio`}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => setBuying(true)} disabled={!selected}
                className="flex min-h-[48px] items-center justify-center gap-2 rounded-xl bg-apple-blue text-sm font-semibold text-white active:opacity-80 disabled:opacity-40">
                <Plus size={15} /> I own this
              </button>
              <button onClick={watch} disabled={!selected || watchState === 'done'}
                className={`flex min-h-[48px] items-center justify-center gap-2 rounded-xl text-sm font-semibold ${
                  watchState === 'done' ? 'bg-apple-green/10 text-green-700'
                    : 'border border-apple-gray-200 bg-white text-apple-gray-700 active:bg-apple-gray-100'
                }`}>
                {watchState === 'done' ? <Check size={15} /> : <Eye size={15} />}
                {watchState === 'done' ? 'Watching' : 'Watch'}
              </button>
            </div>
          )}

          <Link to={`/compass/compare?a=${symbol}`}
            className="flex min-h-[48px] items-center justify-center gap-2 rounded-xl border border-apple-blue/30 bg-apple-blue/5 text-sm font-semibold text-apple-blue active:bg-apple-blue/10">
            <ArrowLeftRight size={15} /> Compare {symbol} with something
          </Link>
          <Link to={`/compass/ask?q=${encodeURIComponent(`Is ${symbol} a good long-term investment for me?`)}`}
            className="flex min-h-[44px] items-center justify-center gap-2 rounded-xl border border-apple-gray-200 bg-white text-sm font-medium text-apple-gray-600 active:bg-apple-gray-100">
            <MessageCircleQuestion size={15} className="text-apple-blue" /> Ask Compass about {symbol}
          </Link>
        </div>
      )}
    </Sheet>
  )
}

interface EtfInsights {
  pros: string[]
  cons: string[]
  best_for: string | null
  similar: { symbol: string; name: string }[]
  note?: string
}

function EtfDetailSheet({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  const { selected } = usePortfolioSelection()
  const [data, setData] = useState<EtfDetail | null>(null)
  const [insights, setInsights] = useState<EtfInsights | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [buying, setBuying] = useState(false)
  const [shares, setShares] = useState('')
  const [cost, setCost] = useState('')
  const [addState, setAddState] = useState<'idle' | 'saving' | 'done'>('idle')
  const [watchState, setWatchState] = useState<'idle' | 'done'>('idle')

  useEffect(() => {
    api.get<EtfDetail>(`/etf/${symbol}`, { timeout: 60000 })
      .then(res => setData(res.data))
      .catch(e => setErr(e.response?.data?.detail || e.message))
    api.get<EtfInsights>(`/etf/${symbol}/insights`, { timeout: 60000 })
      .then(res => setInsights(res.data))
      .catch(() => setInsights(null))
  }, [symbol])

  const addToPortfolio = async () => {
    if (!selected || !parseFloat(shares)) return
    setAddState('saving')
    try {
      await api.post(`/portfolio/${selected}/holding`, {
        symbol, shares: parseFloat(shares), cost_basis: cost ? parseFloat(cost) : 0,
      })
      setAddState('done')
    } catch {
      setAddState('idle')
    }
  }

  const watch = async () => {
    if (!selected) return
    try {
      await api.post(`/portfolio/${selected}/watchlist`, { symbol })
      setWatchState('done')
    } catch { /* non-fatal */ }
  }

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

          {/* Pros / cons / best for */}
          {insights && (insights.pros.length > 0 || insights.best_for) && (
            <div className="animate-fadeUp space-y-2 rounded-xl bg-apple-gray-50 p-3">
              {insights.best_for && (
                <p className="text-xs font-medium leading-relaxed text-apple-gray-700">
                  <span className="font-semibold">Best for:</span> {insights.best_for}
                </p>
              )}
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {insights.pros.length > 0 && (
                  <ul className="space-y-1">
                    {insights.pros.map((p, i) => (
                      <li key={i} className="flex gap-1.5 text-xs leading-snug text-apple-gray-600">
                        <span className="font-bold text-green-600">+</span>{p}
                      </li>
                    ))}
                  </ul>
                )}
                {insights.cons.length > 0 && (
                  <ul className="space-y-1">
                    {insights.cons.map((c, i) => (
                      <li key={i} className="flex gap-1.5 text-xs leading-snug text-apple-gray-600">
                        <span className="font-bold text-apple-orange">–</span>{c}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {/* Similar funds */}
          {(insights?.similar?.length ?? 0) > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-apple-gray-400">Similar funds</p>
              <div className="flex flex-wrap gap-1.5">
                {insights!.similar.map(s => (
                  <Link key={s.symbol} to={`/compass/compare?a=${symbol}&b=${s.symbol}`}
                    className="rounded-full border border-apple-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-apple-gray-600 active:bg-apple-gray-100"
                    title={s.name}>
                    {s.symbol} <span className="text-apple-gray-400">vs</span>
                  </Link>
                ))}
              </div>
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

          {/* Own it / watch it */}
          {addState === 'done' ? (
            <div className="flex min-h-[48px] items-center justify-center gap-2 rounded-xl bg-apple-green/10 text-sm font-semibold text-green-700">
              <Check size={15} /> Added to your portfolio
            </div>
          ) : buying ? (
            <div className="space-y-2 rounded-xl border border-apple-blue/30 bg-apple-blue/5 p-3">
              <div className="grid grid-cols-2 gap-2">
                <input value={shares} onChange={e => setShares(e.target.value)} placeholder="Shares"
                  inputMode="decimal" autoFocus className={inputCls} />
                <MoneyInput value={cost} onChange={setCost} placeholder="Paid each (opt.)" />
              </div>
              <button onClick={addToPortfolio} disabled={addState === 'saving' || !parseFloat(shares)}
                className="flex min-h-[44px] w-full items-center justify-center rounded-xl bg-apple-blue text-sm font-semibold text-white active:opacity-80 disabled:opacity-40">
                {addState === 'saving' ? 'Adding…' : `Add ${symbol} to my portfolio`}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => setBuying(true)} disabled={!selected}
                className="flex min-h-[48px] items-center justify-center gap-2 rounded-xl bg-apple-blue text-sm font-semibold text-white active:opacity-80 disabled:opacity-40">
                <Plus size={15} /> I own this
              </button>
              <button onClick={watch} disabled={!selected || watchState === 'done'}
                className={`flex min-h-[48px] items-center justify-center gap-2 rounded-xl text-sm font-semibold ${
                  watchState === 'done' ? 'bg-apple-green/10 text-green-700'
                    : 'border border-apple-gray-200 bg-white text-apple-gray-700 active:bg-apple-gray-100'
                }`}>
                {watchState === 'done' ? <Check size={15} /> : <Eye size={15} />}
                {watchState === 'done' ? 'Watching' : 'Watch'}
              </button>
            </div>
          )}

          <Link to={`/compass/compare?a=${symbol}`}
            className="flex min-h-[48px] items-center justify-center gap-2 rounded-xl border border-apple-blue/30 bg-apple-blue/5 text-sm font-semibold text-apple-blue active:bg-apple-blue/10">
            <ArrowLeftRight size={15} /> Compare {symbol} with something
          </Link>
          <Link to={`/compass/ask?q=${encodeURIComponent(`Is ${symbol} a good fit for my portfolio?`)}`}
            className="flex min-h-[44px] items-center justify-center gap-2 rounded-xl border border-apple-gray-200 bg-white text-sm font-medium text-apple-gray-600 active:bg-apple-gray-100">
            <MessageCircleQuestion size={15} className="text-apple-blue" /> Ask Compass about {symbol}
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
