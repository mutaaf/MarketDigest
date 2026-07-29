// Compass — Watchlist: things to buy when the price is right.
import { FormEvent, useEffect, useRef, useState } from 'react'
import { Plus, Trash2, BellRing } from 'lucide-react'
import api from '../api/client'
import { SearchResult } from '../api/compass-types'
import {
  EmptyState, ErrorState, GradeChip, MoneyInput, PageSkeleton, Sheet, WarningsBanner,
  inputCls, money, primaryBtn, usePortfolioSelection,
} from '../components/compass/ui'

interface WatchItem {
  symbol: string
  buy_price: number | null
  notes: string
  added: string
  name: string | null
  type: string | null
  price: number | null
  day_change_pct: number | null
  grade: string | null
  above_buy_pct?: number
  at_buy_price?: boolean
}

export default function CompassWatchlist() {
  const { portfolios, selected, error: listError, refresh: refreshList } = usePortfolioSelection()
  const [data, setData] = useState<{ items: WatchItem[]; warnings: string[] } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null)

  const load = () => {
    if (!selected) return
    setError(null)
    api.get(`/portfolio/${selected}/watchlist`, { timeout: 60000 })
      .then(res => setData(res.data))
      .catch(err => setError(err.response?.data?.detail || err.message))
  }
  useEffect(() => { setData(null); load() }, [selected])

  const remove = async (symbol: string) => {
    try {
      await api.delete(`/portfolio/${selected}/watchlist/${symbol}`)
      setConfirmRemove(null)
      load()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  if (listError) return <ErrorState message={listError} onRetry={refreshList} />
  if (portfolios && portfolios.length === 0) {
    return <EmptyState title="No portfolio yet" hint="Create your portfolio on the Portfolio page first." />
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 pb-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-apple-gray-800">Watchlist</h1>
          <p className="text-xs text-apple-gray-500">Things you'd buy at the right price.</p>
        </div>
        <button onClick={() => setShowAdd(true)}
          className="flex min-h-[44px] items-center gap-1.5 rounded-xl bg-apple-blue px-4 text-sm font-semibold text-white active:opacity-80">
          <Plus size={15} /> Add
        </button>
      </div>

      {error && <ErrorState message={error} onRetry={load} />}
      {!data && !error && <PageSkeleton />}

      {data && (
        <>
          <WarningsBanner warnings={data.warnings} />
          {data.items.length === 0 ? (
            <EmptyState
              title="Nothing on your watchlist"
              hint="Add a fund or stock you're interested in, with the price you'd be happy to pay. Compass shows you how close it is."
              action={
                <button onClick={() => setShowAdd(true)} className="min-h-[44px] rounded-xl bg-apple-blue px-6 text-sm font-semibold text-white active:opacity-80">
                  Add my first one
                </button>
              }
            />
          ) : (
            <div className="space-y-2">
              {data.items.map(item => (
                <div key={item.symbol} className={`rounded-2xl border bg-white p-4 ${item.at_buy_price ? 'border-apple-green/50' : 'border-apple-gray-200'}`}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-semibold text-apple-gray-800">
                        {item.symbol}
                        {item.at_buy_price && (
                          <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-apple-green/15 px-2 py-0.5 text-[10px] font-semibold text-green-700">
                            <BellRing size={10} /> At your buy price
                          </span>
                        )}
                      </p>
                      <p className="truncate text-xs text-apple-gray-500">{item.name || ''}</p>
                      {item.notes && <p className="mt-1 text-xs italic text-apple-gray-400">"{item.notes}"</p>}
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <p className="font-semibold tabular-nums text-apple-gray-800">{money(item.price)}</p>
                        {item.buy_price !== null && (
                          <p className="text-xs tabular-nums text-apple-gray-400">
                            want {money(item.buy_price)}
                            {item.above_buy_pct !== undefined && item.above_buy_pct > 0 && (
                              <span className="text-apple-orange"> · {item.above_buy_pct}% above</span>
                            )}
                          </p>
                        )}
                      </div>
                      <GradeChip grade={item.grade} />
                      <button onClick={() => setConfirmRemove(item.symbol)}
                        className="flex min-h-[44px] min-w-[36px] items-center justify-center text-apple-gray-300 active:text-apple-red">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                  {confirmRemove === item.symbol && (
                    <div className="mt-3 flex items-center justify-between gap-3 rounded-xl bg-apple-red/5 px-3 py-2.5">
                      <p className="text-xs text-apple-gray-700">Remove {item.symbol} from your watchlist?</p>
                      <div className="flex shrink-0 gap-2">
                        <button onClick={() => setConfirmRemove(null)} className="min-h-[36px] rounded-lg px-3 text-xs font-medium text-apple-gray-600">Keep</button>
                        <button onClick={() => remove(item.symbol)} className="min-h-[36px] rounded-lg bg-apple-red px-3 text-xs font-semibold text-white">Remove</button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <p className="text-xs text-apple-gray-400">
                Grades fill in as Compass analyzes each symbol (open it on the Compare page to analyze it now).
              </p>
            </div>
          )}
        </>
      )}

      {showAdd && selected && (
        <AddWatchSheet slug={selected} onClose={() => setShowAdd(false)} onSaved={() => { setShowAdd(false); load() }} />
      )}
    </div>
  )
}

function AddWatchSheet({ slug, onClose, onSaved }: { slug: string; onClose: () => void; onSaved: () => void }) {
  const [symbol, setSymbol] = useState('')
  const [buyPrice, setBuyPrice] = useState('')
  const [notes, setNotes] = useState('')
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const timer = useRef<number>()

  const onSymbolChange = (val: string) => {
    setSymbol(val.toUpperCase())
    window.clearTimeout(timer.current)
    if (!val.trim()) { setSuggestions([]); return }
    timer.current = window.setTimeout(() => {
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
      await api.post(`/portfolio/${slug}/watchlist`, {
        symbol: symbol.trim(),
        buy_price: buyPrice ? parseFloat(buyPrice) : null,
        notes,
      })
      onSaved()
    } catch (error: any) {
      setErr(error.response?.data?.detail || "Couldn't add that. Check the symbol and try again.")
      setSaving(false)
    }
  }

  return (
    <Sheet title="Watch a fund or stock" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div className="relative">
          <label className="mb-1 block text-xs font-medium text-apple-gray-500">Ticker symbol</label>
          <input value={symbol} onChange={e => onSymbolChange(e.target.value)} placeholder="e.g. SCHD"
            autoFocus autoCapitalize="characters" autoCorrect="off" className={inputCls} />
          {suggestions.length > 0 && (
            <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-xl border border-apple-gray-200 bg-white shadow-lg">
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
        <div>
          <label className="mb-1 block text-xs font-medium text-apple-gray-500">
            Price you'd buy at <span className="text-apple-gray-300">(optional)</span>
          </label>
          <MoneyInput value={buyPrice} onChange={setBuyPrice} placeholder="25.00" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-apple-gray-500">Note to self <span className="text-apple-gray-300">(optional)</span></label>
          <input value={notes} onChange={e => setNotes(e.target.value)} placeholder="e.g. buy on the next dip" className={inputCls} />
        </div>
        {err && <p className="text-xs text-apple-red">{err}</p>}
        <button type="submit" disabled={saving || !symbol.trim()} className={primaryBtn}>
          {saving ? 'Adding…' : 'Add to watchlist'}
        </button>
      </form>
    </Sheet>
  )
}
