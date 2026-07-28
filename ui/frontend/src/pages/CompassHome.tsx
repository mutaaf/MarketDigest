// Compass — Home: how am I doing, and what should I do next? One glance.
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Sparkles, PiggyBank } from 'lucide-react'
import api from '../api/client'
import { PortfolioSummary, Recommendations } from '../api/compass-types'
import {
  EmptyState, ErrorState, GradeChip, PageSkeleton, Skeleton, money, signed,
  usePortfolioSelection,
} from '../components/compass/ui'

export default function CompassHome() {
  const { portfolios, selected, error: listError, refresh: refreshList } = usePortfolioSelection()
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [recs, setRecs] = useState<Recommendations | null>(null)
  const [recsState, setRecsState] = useState<'loading' | 'ok' | 'error'>('loading')
  const [retire, setRetire] = useState<{ projection: { success_probability: number | null } | null } | null>(null)

  const loadSummary = () => {
    if (!selected) return
    api.get<PortfolioSummary>(`/portfolio/${selected}/summary`)
      .then(res => setSummary(res.data))
      .catch(err => setError(err.response?.data?.detail || err.message))
  }

  useEffect(() => {
    if (!selected) return
    setSummary(null); setRecs(null); setError(null); setRecsState('loading')
    loadSummary()
    api.get<Recommendations>(`/portfolio/${selected}/recommendations`, { timeout: 180000 })
      .then(res => { setRecs(res.data); setRecsState('ok') })
      .catch(() => { setRecs(null); setRecsState('error') })
    api.get(`/portfolio/${selected}/retirement`, { timeout: 60000 })
      .then(res => setRetire(res.data))
      .catch(() => setRetire(null))
  }, [selected])

  // Values refresh quietly every 2 minutes while the page is open
  useEffect(() => {
    if (!selected) return
    const timer = window.setInterval(loadSummary, 120000)
    return () => window.clearInterval(timer)
  }, [selected])

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  if (listError) return <ErrorState message={listError} onRetry={refreshList} />
  if (portfolios && portfolios.length === 0) {
    return (
      <EmptyState
        title="Welcome to Compass"
        hint="Your investing home base. Three quick steps and you'll see how your investments are doing — and what to buy next."
        action={
          <Link to="/compass/welcome" className="flex min-h-[44px] items-center rounded-xl bg-apple-blue px-6 text-sm font-semibold text-white active:opacity-80">
            Get set up
          </Link>
        }
      />
    )
  }
  if (!summary && !error) return <PageSkeleton />
  if (error) return <ErrorState message={error} />

  const v = summary!.valuation
  const topRec = recs?.recommendations?.[0]
  const successProb = retire?.projection?.success_probability ?? null

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-apple-gray-500">{greeting}</p>
        <h1 className="text-xl font-bold text-apple-gray-800">{summary!.name}</h1>
      </div>

      {/* Value + health */}
      <Link to="/compass/portfolio" className="block rounded-2xl border border-apple-gray-200 bg-white p-5 active:bg-apple-gray-50">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-apple-gray-400">Total value</p>
            <p className="mt-1 text-3xl font-bold tabular-nums text-apple-gray-800">{money(v.total_value)}</p>
            <p className={`mt-1 text-sm font-medium tabular-nums ${v.day_change >= 0 ? 'text-green-600' : 'text-apple-red'}`}>
              {signed(v.day_change)} today ({signed(v.day_change_pct, '%')})
            </p>
          </div>
          <div className="text-center">
            <GradeChip grade={summary!.health.grade} size="lg" />
            <p className="mt-1 text-[10px] font-medium uppercase tracking-wide text-apple-gray-400">Health</p>
          </div>
        </div>
        <p className="mt-3 border-t border-apple-gray-100 pt-3 text-xs text-apple-gray-500">{summary!.health.summary}</p>
      </Link>

      {/* Next move */}
      <div className="rounded-2xl border border-apple-gray-200 bg-white p-4">
        <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-apple-gray-400">
          <Sparkles size={13} /> Your next move
        </div>
        {topRec ? (
          <Link to="/compass/ideas" className="mt-1 block active:opacity-70">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-base font-bold text-apple-gray-800">{topRec.symbol} <span className="text-xs font-normal text-apple-gray-400">{topRec.name}</span></p>
                <p className="mt-0.5 text-sm leading-snug text-apple-gray-600">{topRec.reasons[0]}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <GradeChip grade={topRec.grade} />
                <ArrowRight size={16} className="text-apple-gray-300" />
              </div>
            </div>
          </Link>
        ) : recsState === 'loading' ? (
          <>
            <Skeleton className="mt-1 h-12 w-full" />
            <p className="mt-1 text-[11px] text-apple-gray-400">Analyzing today's fund data — the first look can take a minute.</p>
          </>
        ) : recsState === 'error' ? (
          <p className="text-sm text-apple-gray-500">
            Couldn't finish analyzing just now. <Link to="/compass/ideas" className="text-apple-blue">Open Ideas to retry</Link>.
          </p>
        ) : (
          <p className="text-sm text-apple-gray-500">Add holdings or cash and Compass will suggest what to buy next.</p>
        )}
      </div>

      {/* Retirement + Ask quick cards */}
      <div className="grid grid-cols-2 gap-3">
        <Link to="/compass/retire" className="rounded-2xl border border-apple-gray-200 bg-white p-4 active:bg-apple-gray-50">
          <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-apple-gray-400">
            <PiggyBank size={13} /> Retirement
          </div>
          {successProb !== null ? (
            <>
              <p className={`mt-1 text-2xl font-bold tabular-nums ${successProb >= 85 ? 'text-green-600' : successProb >= 60 ? 'text-yellow-600' : 'text-apple-red'}`}>
                {successProb.toFixed(0)}%
              </p>
              <p className="text-[11px] text-apple-gray-400">chance your plan works</p>
            </>
          ) : (
            <p className="mt-1 text-sm text-apple-gray-500">Set up your plan — it takes a minute.</p>
          )}
        </Link>
        <Link to="/compass/ask" className="rounded-2xl border border-apple-gray-200 bg-white p-4 active:bg-apple-gray-50">
          <div className="text-xs font-semibold uppercase tracking-wide text-apple-gray-400">Ask Compass</div>
          <p className="mt-1 text-sm leading-snug text-apple-gray-600">"Should I buy more VOO?" — ask anything about your money.</p>
        </Link>
      </div>
    </div>
  )
}
