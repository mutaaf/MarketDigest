// Compass — Portfolio: holdings, value, allocation. Mobile-first.
import { FormEvent, useEffect, useRef, useState } from 'react'
import { Plus, Trash2, Upload, Wallet } from 'lucide-react'
import api from '../api/client'
import { PortfolioSummary, SearchResult } from '../api/compass-types'
import {
  AllocationBars, EmptyState, ErrorState, GradeChip, PageSkeleton, Sheet,
  WarningsBanner, inputCls, money, primaryBtn, signed, usePortfolioSelection,
} from '../components/compass/ui'
import SmartImport from '../components/compass/SmartImport'

export default function CompassPortfolio() {
  const { portfolios, selected, setSelected, refresh: refreshList, error: listError } = usePortfolioSelection()
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sheet, setSheet] = useState<'add' | 'cash' | 'import' | 'create' | 'deletePortfolio' | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  const loadSummary = () => {
    if (!selected) return
    setLoading(true)
    setError(null)
    api.get<PortfolioSummary>(`/portfolio/${selected}/summary`)
      .then(res => setSummary(res.data))
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }
  useEffect(loadSummary, [selected])

  // Prices refresh quietly every 2 minutes while the page is open
  useEffect(() => {
    if (!selected) return
    const timer = window.setInterval(loadSummary, 120000)
    return () => window.clearInterval(timer)
  }, [selected])

  const deleteHolding = async (symbol: string) => {
    try {
      await api.delete(`/portfolio/${selected}/holding/${symbol}`)
      setConfirmDelete(null)
      loadSummary()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  if (listError) return <ErrorState message={listError} onRetry={refreshList} />

  if (portfolios && portfolios.length === 0) {
    return (
      <div className="mx-auto max-w-xl">
        <EmptyState
          title="Welcome to Compass"
          hint="Start with the guided setup — it walks you through adding what you own and picking a plan."
          action={
            <a href="/compass/welcome" className="flex min-h-[44px] items-center rounded-xl bg-apple-blue px-6 text-sm font-semibold text-white active:opacity-80">
              Get set up
            </a>
          }
        />
      </div>
    )
  }

  const v = summary?.valuation

  return (
    <div className="mx-auto max-w-3xl space-y-4 pb-6">
      {/* Portfolio picker */}
      <div className="flex items-center gap-2">
        <select
          value={selected}
          onChange={e => setSelected(e.target.value)}
          className="min-h-[44px] flex-1 rounded-xl border border-apple-gray-200 bg-white px-3 text-sm font-medium text-apple-gray-800"
        >
          {(portfolios ?? []).map(p => (
            <option key={p.slug} value={p.slug}>{p.name}</option>
          ))}
        </select>
        <button onClick={() => setSheet('create')} title="New portfolio"
          className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-apple-gray-200 bg-white text-apple-gray-600 active:bg-apple-gray-100">
          <Plus size={18} />
        </button>
        <button onClick={() => setSheet('deletePortfolio')} title="Delete this portfolio"
          className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-apple-gray-200 bg-white text-apple-gray-300 active:text-apple-red">
          <Trash2 size={16} />
        </button>
      </div>

      {loading && !summary && <PageSkeleton />}
      {error && <ErrorState message={error} onRetry={loadSummary} />}

      {summary && v && (
        <>
          {/* Value header */}
          <div className="rounded-2xl bg-white p-5 shadow-sm border border-apple-gray-200">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-apple-gray-400">Total value</p>
                <p className="mt-1 text-3xl font-bold tabular-nums text-apple-gray-800">{money(v.total_value)}</p>
                <p className={`mt-1 text-sm font-medium tabular-nums ${v.day_change >= 0 ? 'text-green-600' : 'text-apple-red'}`}>
                  {signed(v.day_change)} today ({signed(v.day_change_pct, '%')})
                </p>
              </div>
              <GradeChip grade={summary.health.grade} size="lg" />
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 border-t border-apple-gray-100 pt-3 text-center">
              <Stat label="Invested" value={money(v.invested_value)} />
              <Stat label="Cash" value={money(v.cash)} onClick={() => setSheet('cash')} />
              <Stat label="Total gain" value={v.total_gain !== null ? signed(v.total_gain) : '—'}
                tone={v.total_gain === null ? undefined : v.total_gain >= 0 ? 'green' : 'red'} />
            </div>
          </div>

          <WarningsBanner warnings={v.warnings} />

          {/* Holdings */}
          <section>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-apple-gray-500">Holdings</h2>
              <div className="flex gap-2">
                <button onClick={() => setSheet('import')}
                  className="flex min-h-[36px] items-center gap-1.5 rounded-lg border border-apple-gray-200 bg-white px-3 text-xs font-medium text-apple-gray-600 active:bg-apple-gray-100">
                  <Upload size={13} /> Import
                </button>
                <button onClick={() => setSheet('add')}
                  className="flex min-h-[36px] items-center gap-1.5 rounded-lg bg-apple-blue px-3 text-xs font-semibold text-white active:opacity-80">
                  <Plus size={13} /> Add
                </button>
              </div>
            </div>

            {v.holdings.length === 0 ? (
              <EmptyState
                title="No holdings yet"
                hint="Add what you own — a ticker like VOO or AAPL, how many shares, and what you paid. Or import a CSV from your broker."
                action={
                  <button onClick={() => setSheet('add')} className="min-h-[44px] rounded-xl bg-apple-blue px-6 text-sm font-semibold text-white active:opacity-80">
                    Add my first holding
                  </button>
                }
              />
            ) : (
              <div className="space-y-2">
                {summary.allocation.by_holding.map(h => (
                  <div key={h.symbol} className="rounded-2xl border border-apple-gray-200 bg-white p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-semibold text-apple-gray-800">
                          {h.symbol}
                          <span className="ml-2 text-xs font-normal text-apple-gray-400">
                            {h.instrument_type === 'etf' ? 'Fund' : h.instrument_type === 'stock' ? 'Stock' : ''}
                          </span>
                        </p>
                        <p className="truncate text-xs text-apple-gray-500">{h.display_name || ''}</p>
                        <p className="mt-1 text-xs tabular-nums text-apple-gray-500">
                          {h.shares} shares {h.price !== null ? `@ ${money(h.price)}` : '· price unavailable'}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold tabular-nums text-apple-gray-800">{money(h.value)}</p>
                        <p className="text-xs tabular-nums text-apple-gray-400">{h.weight.toFixed(1)}% of portfolio</p>
                        {h.gain_pct !== null && (
                          <p className={`text-xs font-medium tabular-nums ${h.gain_pct >= 0 ? 'text-green-600' : 'text-apple-red'}`}>
                            {signed(h.gain_pct, '%')} all time
                          </p>
                        )}
                      </div>
                      <button
                        onClick={() => setConfirmDelete(h.symbol)}
                        title={`Remove ${h.symbol}`}
                        className="flex min-h-[44px] min-w-[36px] items-center justify-center text-apple-gray-300 active:text-apple-red">
                        <Trash2 size={16} />
                      </button>
                    </div>
                    {confirmDelete === h.symbol && (
                      <div className="mt-3 flex items-center justify-between gap-3 rounded-xl bg-apple-red/5 px-3 py-2.5">
                        <p className="text-xs text-apple-gray-700">Remove {h.symbol} from this portfolio? Your brokerage account is not affected.</p>
                        <div className="flex shrink-0 gap-2">
                          <button onClick={() => setConfirmDelete(null)} className="min-h-[36px] rounded-lg px-3 text-xs font-medium text-apple-gray-600">Keep</button>
                          <button onClick={() => deleteHolding(h.symbol)} className="min-h-[36px] rounded-lg bg-apple-red px-3 text-xs font-semibold text-white">Remove</button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Allocation */}
          {v.holdings.length > 0 && (
            <>
              <section className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-apple-gray-200 bg-white p-4">
                  <h3 className="mb-3 text-sm font-semibold text-apple-gray-700">What you own, by type</h3>
                  <AllocationBars slices={summary.allocation.asset_classes} />
                </div>
                <div className="rounded-2xl border border-apple-gray-200 bg-white p-4">
                  <h3 className="mb-3 text-sm font-semibold text-apple-gray-700">By industry</h3>
                  <AllocationBars slices={summary.allocation.sectors} />
                </div>
                <div className="rounded-2xl border border-apple-gray-200 bg-white p-4">
                  <h3 className="mb-3 text-sm font-semibold text-apple-gray-700">Where in the world</h3>
                  <AllocationBars slices={summary.allocation.geography} />
                </div>
                <div className="rounded-2xl border border-apple-gray-200 bg-white p-4">
                  <h3 className="mb-3 text-sm font-semibold text-apple-gray-700">Company size</h3>
                  <AllocationBars slices={summary.allocation.market_caps.filter(s => s.key !== 'Not stocks')} />
                </div>
              </section>
              <section className="rounded-2xl border border-apple-gray-200 bg-white p-4">
                <h3 className="mb-2 text-sm font-semibold text-apple-gray-700">Portfolio character</h3>
                <div className="space-y-1.5 text-xs leading-relaxed text-apple-gray-500">
                  {summary.allocation.weighted_beta !== null && (
                    <p>
                      <strong className="text-apple-gray-700">Choppiness (beta): {summary.allocation.weighted_beta.toFixed(2)}</strong>
                      {' — '}
                      {summary.allocation.weighted_beta > 1.15
                        ? 'your portfolio swings harder than the overall market.'
                        : summary.allocation.weighted_beta < 0.85
                          ? 'your portfolio moves more gently than the overall market.'
                          : 'your portfolio roughly moves with the overall market.'}
                    </p>
                  )}
                  {summary.allocation.weighted_yield !== null && (
                    <p>
                      <strong className="text-apple-gray-700">Dividends: ~{summary.allocation.weighted_yield.toFixed(1)}%/yr</strong>
                      {' — '}about {money(v.invested_value * summary.allocation.weighted_yield / 100)} a year in
                      dividend payments at today's rates.
                    </p>
                  )}
                  {summary.allocation.weighted_expense_ratio !== null && (
                    <p>
                      <strong className="text-apple-gray-700">Fund costs: {summary.allocation.weighted_expense_ratio.toFixed(2)}%/yr</strong>
                      {' — '}about ${Math.round(summary.allocation.weighted_expense_ratio * 100)} per $10,000 invested.
                    </p>
                  )}
                </div>
              </section>
            </>
          )}
        </>
      )}

      {sheet === 'add' && selected && (
        <AddHoldingSheet slug={selected} onClose={() => setSheet(null)} onSaved={() => { setSheet(null); loadSummary() }} />
      )}
      {sheet === 'cash' && selected && summary && (
        <CashSheet slug={selected} current={summary.valuation.cash} onClose={() => setSheet(null)} onSaved={() => { setSheet(null); loadSummary() }} />
      )}
      {sheet === 'import' && selected && (
        <ImportSheet slug={selected} onClose={() => setSheet(null)} onSaved={() => { setSheet(null); loadSummary() }} />
      )}
      {sheet === 'create' && (
        <CreateSheet onClose={() => setSheet(null)} onCreated={slug => { setSheet(null); refreshList(); setSelected(slug) }} />
      )}
      {sheet === 'deletePortfolio' && selected && summary && (
        <DeletePortfolioSheet
          slug={selected}
          name={summary.name}
          holdingsCount={summary.valuation.holdings.length}
          onClose={() => setSheet(null)}
          onDeleted={() => { setSheet(null); setSummary(null); refreshList() }}
        />
      )}
    </div>
  )
}

function DeletePortfolioSheet({ slug, name, holdingsCount, onClose, onDeleted }: {
  slug: string; name: string; holdingsCount: number; onClose: () => void; onDeleted: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const confirm = async () => {
    setBusy(true)
    setErr(null)
    try {
      await api.delete(`/portfolio/${slug}`)
      onDeleted()
    } catch (error: any) {
      setErr(error.response?.data?.detail || "Couldn't delete the portfolio.")
      setBusy(false)
    }
  }

  return (
    <Sheet title={`Delete "${name}"?`} onClose={onClose}>
      <div className="space-y-3">
        <p className="text-sm leading-relaxed text-apple-gray-600">
          This permanently removes this portfolio ({holdingsCount} holding{holdingsCount === 1 ? '' : 's'}) and
          its watchlist from Compass. Your actual brokerage accounts are not affected — Compass only tracks
          what you typed in.
        </p>
        {err && <p className="text-xs text-apple-red">{err}</p>}
        <div className="grid grid-cols-2 gap-2">
          <button onClick={onClose} className="min-h-[48px] rounded-xl border border-apple-gray-200 bg-white text-sm font-semibold text-apple-gray-700 active:bg-apple-gray-100">
            Keep it
          </button>
          <button onClick={confirm} disabled={busy}
            className="min-h-[48px] rounded-xl bg-apple-red text-sm font-semibold text-white active:opacity-80 disabled:opacity-40">
            {busy ? 'Deleting…' : 'Delete portfolio'}
          </button>
        </div>
      </div>
    </Sheet>
  )
}

function Stat({ label, value, tone, onClick }: { label: string; value: string; tone?: 'green' | 'red'; onClick?: () => void }) {
  const color = tone === 'green' ? 'text-green-600' : tone === 'red' ? 'text-apple-red' : 'text-apple-gray-800'
  const inner = (
    <>
      <p className="text-[11px] font-medium uppercase tracking-wide text-apple-gray-400">{label}</p>
      <p className={`mt-0.5 text-sm font-semibold tabular-nums ${color}`}>{value}</p>
    </>
  )
  if (onClick) {
    return <button onClick={onClick} className="rounded-xl py-1 active:bg-apple-gray-50">{inner}<p className="text-[10px] text-apple-blue">edit</p></button>
  }
  return <div className="py-1">{inner}</div>
}

function AddHoldingSheet({ slug, onClose, onSaved }: { slug: string; onClose: () => void; onSaved: () => void }) {
  const [symbol, setSymbol] = useState('')
  const [shares, setShares] = useState('')
  const [cost, setCost] = useState('')
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const searchTimer = useRef<number>()

  const onSymbolChange = (val: string) => {
    setSymbol(val.toUpperCase())
    window.clearTimeout(searchTimer.current)
    if (val.trim().length < 1) { setSuggestions([]); return }
    searchTimer.current = window.setTimeout(() => {
      api.get<{ results: SearchResult[] }>('/compass/search', { params: { q: val } })
        .then(res => setSuggestions(res.data.results.slice(0, 5)))
        .catch(() => setSuggestions([]))
    }, 200)
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setErr(null)
    try {
      await api.post(`/portfolio/${slug}/holding`, {
        symbol: symbol.trim(), shares: parseFloat(shares), cost_basis: cost ? parseFloat(cost) : 0,
      })
      onSaved()
    } catch (error: any) {
      setErr(error.response?.data?.detail || "Couldn't save that. Check the numbers and try again.")
      setSaving(false)
    }
  }

  return (
    <Sheet title="Add a holding" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-apple-gray-500">Ticker symbol</label>
          <input value={symbol} onChange={e => onSymbolChange(e.target.value)} placeholder="e.g. VOO or AAPL"
            autoFocus autoCapitalize="characters" autoCorrect="off" className={inputCls} />
          {suggestions.length > 0 && (
            <div className="mt-1 overflow-hidden rounded-xl border border-apple-gray-200 bg-white">
              {suggestions.map(s => (
                <button key={s.symbol} type="button"
                  onClick={() => { setSymbol(s.symbol); setSuggestions([]) }}
                  className="flex w-full items-center justify-between px-3 py-2.5 text-left text-sm active:bg-apple-gray-50">
                  <span className="font-medium">{s.symbol}</span>
                  <span className="ml-2 truncate text-xs text-apple-gray-400">{s.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-apple-gray-500">Shares</label>
            <input value={shares} onChange={e => setShares(e.target.value)} placeholder="10" inputMode="decimal" className={inputCls} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-apple-gray-500">Price paid per share <span className="text-apple-gray-300">(optional)</span></label>
            <input value={cost} onChange={e => setCost(e.target.value)} placeholder="380.50" inputMode="decimal" className={inputCls} />
          </div>
        </div>
        {err && <p className="text-xs text-apple-red">{err}</p>}
        <button type="submit" disabled={saving || !symbol.trim() || !parseFloat(shares)} className={primaryBtn}>
          {saving ? 'Saving…' : 'Add holding'}
        </button>
      </form>
    </Sheet>
  )
}

function CashSheet({ slug, current, onClose, onSaved }: { slug: string; current: number; onClose: () => void; onSaved: () => void }) {
  const [amount, setAmount] = useState(String(current || ''))
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setErr(null)
    try {
      await api.put(`/portfolio/${slug}/cash`, { amount: parseFloat(amount) || 0 })
      onSaved()
    } catch (error: any) {
      setErr(error.response?.data?.detail || "Couldn't save that amount.")
      setSaving(false)
    }
  }

  return (
    <Sheet title="Cash available to invest" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <p className="text-xs text-apple-gray-500">
          <Wallet size={13} className="mr-1 inline" />
          Money sitting in your brokerage account waiting to be invested. Compass uses this for its recommendations.
        </p>
        <input value={amount} onChange={e => setAmount(e.target.value)} inputMode="decimal" placeholder="5000" autoFocus className={inputCls} />
        {err && <p className="text-xs text-apple-red">{err}</p>}
        <button type="submit" disabled={saving} className={primaryBtn}>{saving ? 'Saving…' : 'Save'}</button>
      </form>
    </Sheet>
  )
}

function ImportSheet({ slug, onClose, onSaved }: { slug: string; onClose: () => void; onSaved: () => void }) {
  return (
    <Sheet title="Bring in your holdings" onClose={onClose}>
      <SmartImport slug={slug} onDone={onSaved} />
    </Sheet>
  )
}

function CreateSheet({ onClose, onCreated }: { onClose: () => void; onCreated: (slug: string) => void }) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setErr(null)
    try {
      const res = await api.post('/portfolio/create', { name: name.trim() })
      const slug = (res.data.name as string).toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '')
      onCreated(slug)
    } catch (error: any) {
      setErr(error.response?.data?.detail || "Couldn't create the portfolio.")
      setBusy(false)
    }
  }

  return (
    <Sheet title="New portfolio" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <p className="text-xs text-apple-gray-500">Give it a name — usually just whose money it is.</p>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Sarah's Investments" autoFocus className={inputCls} />
        {err && <p className="text-xs text-apple-red">{err}</p>}
        <button type="submit" disabled={busy || !name.trim()} className={primaryBtn}>
          {busy ? 'Creating…' : 'Create portfolio'}
        </button>
      </form>
    </Sheet>
  )
}
