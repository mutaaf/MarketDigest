// Compass — Ideas: portfolio health check + "what should I buy next?"
import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CheckCircle2, AlertCircle, MinusCircle, RefreshCw, Sparkles, SlidersHorizontal,
  Copy, ChevronDown, Eye, ArrowLeftRight, MessageCircleQuestion, Check,
} from 'lucide-react'
import api from '../api/client'
import { PortfolioSummary, Recommendations } from '../api/compass-types'
import {
  EmptyState, ErrorState, GradeChip, PageSkeleton, ScoreRing, Sheet, Skeleton,
  WarningsBanner, inputCls, money, primaryBtn, usePortfolioSelection,
} from '../components/compass/ui'
import RulesOfThumb from '../components/compass/RulesOfThumb'
import { projectLocal, RetireInputs } from '../components/compass/retirementMath'
import { PiggyBank, ArrowRight } from 'lucide-react'

const TARGET_CLASSES: { key: string; label: string; fallback: number }[] = [
  { key: 'us_stock', label: 'US stocks', fallback: 55 },
  { key: 'intl_stock', label: 'International', fallback: 20 },
  { key: 'bond', label: 'Bonds', fallback: 15 },
  { key: 'reit', label: 'Real estate', fallback: 5 },
  { key: 'crypto', label: 'Crypto', fallback: 0 },
  { key: 'cash', label: 'Cash', fallback: 5 },
]

const statusIcon = {
  good: <CheckCircle2 size={18} className="text-green-600" />,
  ok: <MinusCircle size={18} className="text-yellow-600" />,
  warn: <AlertCircle size={18} className="text-apple-orange" />,
}

export default function CompassIdeas() {
  const { portfolios, selected, error: listError, refresh: refreshList } = usePortfolioSelection()
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [summaryError, setSummaryError] = useState<string | null>(null)
  const [recs, setRecs] = useState<Recommendations | null>(null)
  const [recsLoading, setRecsLoading] = useState(false)
  const [recsError, setRecsError] = useState<string | null>(null)
  const [showTargets, setShowTargets] = useState(false)
  const [openFactor, setOpenFactor] = useState<string | null>(null)
  const [watched, setWatched] = useState<Set<string>>(new Set())
  const [retireInputs, setRetireInputs] = useState<Record<string, number> | null>(null)

  useEffect(() => {
    if (!selected) return
    api.get(`/portfolio/${selected}/retirement`, { timeout: 60000 })
      .then(res => setRetireInputs(res.data.inputs || {}))
      .catch(() => setRetireInputs({}))
  }, [selected])

  const addToWatchlist = async (symbol: string) => {
    try {
      await api.post(`/portfolio/${selected}/watchlist`, { symbol })
      setWatched(prev => new Set(prev).add(symbol))
    } catch { /* non-fatal */ }
  }

  const loadSummary = () => {
    if (!selected) return
    setSummaryError(null)
    api.get<PortfolioSummary>(`/portfolio/${selected}/summary`)
      .then(res => setSummary(res.data))
      .catch(err => setSummaryError(err.response?.data?.detail || err.message))
  }

  const loadRecs = () => {
    if (!selected) return
    setRecsLoading(true)
    setRecsError(null)
    api.get<Recommendations>(`/portfolio/${selected}/recommendations`, { timeout: 180000 })
      .then(res => setRecs(res.data))
      .catch(err => setRecsError(err.response?.data?.detail || err.message))
      .finally(() => setRecsLoading(false))
  }

  useEffect(() => { setSummary(null); setRecs(null); loadSummary(); loadRecs() }, [selected])

  if (listError) return <ErrorState message={listError} onRetry={refreshList} />
  if (portfolios && portfolios.length === 0) {
    return <EmptyState title="No portfolio yet" hint="Create your portfolio on the Portfolio page first — then Compass can check its health and suggest what to buy." />
  }
  if (!summary && !summaryError) return <PageSkeleton />

  return (
    <div className="mx-auto max-w-3xl space-y-5 pb-6">
      {/* Health */}
      {summaryError ? (
        <ErrorState message={summaryError} onRetry={loadSummary} />
      ) : summary && (
        <section className="animate-fadeUp rounded-2xl border border-apple-gray-200 bg-white p-5">
          <div className="flex items-center gap-4">
            <ScoreRing score={summary.health.score ?? 0}>
              <GradeChip grade={summary.health.grade} size="lg" />
            </ScoreRing>
            <div>
              <h2 className="text-base font-semibold text-apple-gray-800">Portfolio health</h2>
              <p className="mt-0.5 text-sm text-apple-gray-500">{summary.health.summary}</p>
              {summary.health.score !== null && (
                <p className="mt-0.5 text-xs tabular-nums text-apple-gray-400">{summary.health.score.toFixed(0)} / 100</p>
              )}
            </div>
          </div>
          {summary.health.factors.length > 0 && (
            <div className="mt-4 space-y-1 border-t border-apple-gray-100 pt-3">
              {summary.health.factors.map((f, i) => {
                const open = openFactor === f.name
                return (
                  <div key={f.name} className="animate-fadeUp" style={{ animationDelay: `${i * 60}ms` }}>
                    <button onClick={() => setOpenFactor(open ? null : f.name)}
                      className="flex w-full items-start gap-3 rounded-xl px-1 py-2 text-left active:bg-apple-gray-50">
                      <div className="mt-0.5 shrink-0">{statusIcon[f.status]}</div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-apple-gray-800">{f.name}</p>
                        <p className="text-xs leading-relaxed text-apple-gray-500">{f.detail}</p>
                      </div>
                      <ChevronDown size={14} className={`mt-1 shrink-0 text-apple-gray-300 transition-transform ${open ? 'rotate-180' : ''}`} />
                    </button>
                    {open && (
                      <Link
                        to={`/compass/ask?q=${encodeURIComponent(`My portfolio health check flagged "${f.name}": ${f.detail} What are simple ways to improve this?`)}`}
                        className="mb-2 ml-8 flex min-h-[40px] items-center gap-2 rounded-xl bg-apple-blue/5 px-3 text-xs font-medium text-apple-blue active:bg-apple-blue/10"
                      >
                        <MessageCircleQuestion size={13} /> Ask Compass how to improve this
                      </Link>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </section>
      )}

      {/* Overlap check */}
      {summary && summary.overlap && summary.overlap.findings.length > 0 && (
        <section className="rounded-2xl border border-apple-gray-200 bg-white p-4">
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-apple-gray-700">
            <Copy size={14} className="text-apple-orange" /> Owning the same thing twice
          </h3>
          <div className="space-y-2">
            {summary.overlap.findings.map((f, i) => (
              <p key={i} className="text-xs leading-relaxed text-apple-gray-600">
                {f.text}
                {f.overlap_pct !== undefined && (
                  <span className="text-apple-gray-400"> (~{f.overlap_pct.toFixed(0)}% overlap)</span>
                )}
              </p>
            ))}
          </div>
          <p className="mt-2 border-t border-apple-gray-100 pt-2 text-[10px] text-apple-gray-400">
            {summary.overlap.note} Overlap isn't automatically bad — it just means less variety than the
            number of holdings suggests.
          </p>
        </section>
      )}

      {/* Retirement goal bridge */}
      {summary && retireInputs && summary.valuation.total_value > 0 && (
        <RetirementGoalCard inputs={retireInputs} liveAssets={summary.valuation.total_value} />
      )}

      {/* Rules of thumb */}
      {summary && summary.valuation.total_value > 0 && (
        <RulesOfThumb
          invested={summary.valuation.invested_value}
          cash={summary.valuation.cash}
          stockPct={(summary.allocation.asset_classes.find(c => c.key === 'us_stock')?.weight ?? 0)
            + (summary.allocation.asset_classes.find(c => c.key === 'intl_stock')?.weight ?? 0)}
          age={retireInputs?.current_age ?? null}
          monthlySpending={retireInputs?.monthly_spending ?? null}
          expectedReturnPct={retireInputs?.expected_return_pct ?? null}
        />
      )}

      {/* Target vs actual */}
      {summary && summary.valuation.holdings.length > 0 && (
        <section className="rounded-2xl border border-apple-gray-200 bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-apple-gray-700">Your mix vs your plan</h3>
            <button onClick={() => setShowTargets(true)}
              className="flex min-h-[36px] items-center gap-1.5 rounded-lg border border-apple-gray-200 bg-white px-3 text-xs font-medium text-apple-gray-600 active:bg-apple-gray-100">
              <SlidersHorizontal size={13} /> Set targets
            </button>
          </div>
          <div className="space-y-3">
            {TARGET_CLASSES.map(tc => {
              const actual = summary.allocation.asset_classes.find(c => c.key === tc.key)?.weight ?? 0
              const target = summary.targets[tc.key] ?? (Object.keys(summary.targets).length ? 0 : tc.fallback)
              const diff = actual - target
              return (
                <div key={tc.key}>
                  <div className="mb-1 flex items-baseline justify-between text-xs">
                    <span className="text-apple-gray-600">{tc.label}</span>
                    <span className="tabular-nums text-apple-gray-500">
                      {actual.toFixed(0)}% of {target.toFixed(0)}%
                      {Math.abs(diff) >= 3 && (
                        <span className={diff < 0 ? 'ml-1 text-apple-orange' : 'ml-1 text-apple-gray-400'}>
                          · {diff < 0 ? `${Math.abs(diff).toFixed(0)} under` : `${diff.toFixed(0)} over`}
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="relative h-2 overflow-hidden rounded-full bg-apple-gray-100">
                    <div className="h-full rounded-full bg-apple-blue transition-all duration-500"
                      style={{ width: `${Math.min(100, actual)}%` }} />
                    <div className="absolute top-[-2px] h-3 w-0.5 bg-apple-gray-500"
                      style={{ left: `${Math.min(100, target)}%` }} title={`Target ${target}%`} />
                  </div>
                </div>
              )
            })}
          </div>
          {!Object.keys(summary.targets).length && (
            <p className="mt-3 text-[11px] text-apple-gray-400">
              Using a standard long-term mix until you set your own targets.
            </p>
          )}
        </section>
      )}

      {/* Recommendations */}
      <section>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide text-apple-gray-500">
            <Sparkles size={14} /> What should I buy next?
          </h2>
          <button onClick={loadRecs} disabled={recsLoading}
            className="flex min-h-[36px] items-center gap-1.5 rounded-lg border border-apple-gray-200 bg-white px-3 text-xs font-medium text-apple-gray-600 active:bg-apple-gray-100 disabled:opacity-40">
            <RefreshCw size={13} className={recsLoading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>

        {recs?.cash_available ? (
          <p className="mb-3 text-sm text-apple-gray-600">
            You have <strong>{money(recs.cash_available)}</strong> ready to invest. Here's where it would help most:
          </p>
        ) : null}

        {recsLoading && !recs && (
          <div className="space-y-3">
            <p className="rounded-xl bg-apple-blue/5 px-4 py-3 text-sm text-apple-gray-600">
              Analyzing your portfolio and today's fund data… the first run can take up to a minute.
            </p>
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        )}

        {recsError && <ErrorState message={recsError} onRetry={loadRecs} />}

        {recs && (
          <>
            <WarningsBanner warnings={recs.warnings} />
            {recs.note && <EmptyState title="Nothing to recommend yet" hint={recs.note} />}
            <div className="mt-2 space-y-3">
              {recs.recommendations.map((r, i) => (
                <div key={r.symbol} className="animate-fadeUp rounded-2xl border border-apple-gray-200 bg-white p-4" style={{ animationDelay: `${i * 80}ms` }}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-medium text-apple-gray-400">#{i + 1} pick · {r.type === 'etf' ? 'Fund' : 'Stock'}</p>
                      <p className="text-lg font-bold text-apple-gray-800">{r.symbol}</p>
                      <p className="text-xs text-apple-gray-500">{r.name}</p>
                    </div>
                    <GradeChip grade={r.grade} />
                  </div>
                  <ul className="mt-3 space-y-1.5 border-t border-apple-gray-100 pt-3">
                    {r.reasons.map((reason, j) => (
                      <li key={j} className="flex gap-2 text-sm leading-relaxed text-apple-gray-600">
                        <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-apple-blue" />
                        {reason}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-3 grid grid-cols-3 gap-1.5 border-t border-apple-gray-100 pt-3">
                    <button onClick={() => addToWatchlist(r.symbol)} disabled={watched.has(r.symbol)}
                      className={`flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl text-xs font-medium ${
                        watched.has(r.symbol)
                          ? 'bg-apple-green/10 text-green-700'
                          : 'border border-apple-gray-200 bg-white text-apple-gray-600 active:bg-apple-gray-100'
                      }`}>
                      {watched.has(r.symbol) ? <Check size={13} /> : <Eye size={13} />}
                      {watched.has(r.symbol) ? 'Watching' : 'Watch'}
                    </button>
                    <Link to={`/compass/compare?a=${r.symbol}`}
                      className="flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl border border-apple-gray-200 bg-white text-xs font-medium text-apple-gray-600 active:bg-apple-gray-100">
                      <ArrowLeftRight size={13} /> Compare
                    </Link>
                    <Link to={`/compass/ask?q=${encodeURIComponent(`Compass recommended ${r.symbol} for me. Walk me through whether it makes sense.`)}`}
                      className="flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl border border-apple-gray-200 bg-white text-xs font-medium text-apple-gray-600 active:bg-apple-gray-100">
                      <MessageCircleQuestion size={13} /> Ask
                    </Link>
                  </div>
                </div>
              ))}
            </div>
            {recs.targets_are_default && recs.recommendations.length > 0 && (
              <p className="mt-3 text-xs text-apple-gray-400">
                Based on a standard long-term mix (55% US stocks, 20% international, 15% bonds, 5% real estate).
                Use "Set targets" above to make it yours.
              </p>
            )}
          </>
        )}
      </section>

      {showTargets && selected && summary && (
        <TargetsSheet
          slug={selected}
          current={summary.targets}
          onClose={() => setShowTargets(false)}
          onSaved={() => { setShowTargets(false); loadSummary(); loadRecs() }}
        />
      )}
    </div>
  )
}

function RetirementGoalCard({ inputs, liveAssets }: { inputs: Record<string, number>; liveAssets: number }) {
  const ready = inputs.current_age && inputs.retire_age && inputs.monthly_spending
  if (!ready) {
    return (
      <section className="animate-fadeUp rounded-2xl border border-apple-gray-200 bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <PiggyBank size={16} className="text-apple-blue" />
            <p className="text-sm text-apple-gray-600">Set a retirement goal and these picks start working toward it.</p>
          </div>
          <Link to="/compass/retire" className="flex shrink-0 items-center gap-1 text-xs font-semibold text-apple-blue">
            Set up <ArrowRight size={12} />
          </Link>
        </div>
      </section>
    )
  }

  // Use the LIVE portfolio value as the starting assets — the plan follows the money
  const base: RetireInputs = {
    current_age: inputs.current_age,
    retire_age: inputs.retire_age,
    current_assets: liveAssets,
    monthly_contribution: inputs.monthly_contribution ?? 0,
    monthly_spending: inputs.monthly_spending,
    expected_return_pct: inputs.expected_return_pct ?? 7,
  }
  const now = projectLocal(base)
  const needed = inputs.monthly_spending * 12 * 25
  const pct = Math.min(100, now.projected / needed * 100)
  const plus100 = projectLocal({ ...base, monthly_contribution: base.monthly_contribution + 100 }).projected - now.projected
  const plus2yr = projectLocal({ ...base, retire_age: base.retire_age + 2 }).projected - now.projected

  return (
    <section className="animate-fadeUp rounded-2xl border border-apple-gray-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-sm font-semibold text-apple-gray-700">
          <PiggyBank size={14} className="text-apple-blue" /> Your retirement goal
        </h3>
        <Link to="/compass/retire" className="flex items-center gap-1 text-xs font-medium text-apple-blue">
          Adjust <ArrowRight size={12} />
        </Link>
      </div>
      <p className="text-sm text-apple-gray-600">
        On track for <strong className="text-apple-gray-800">{money(now.projected)}</strong> at {base.retire_age} —{' '}
        {pct >= 100 ? 'past' : `${pct.toFixed(0)}% of`} the <strong className="text-apple-gray-800">{money(needed)}</strong>{' '}
        that supports {money(inputs.monthly_spending)}/month forever.
      </p>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-apple-gray-100">
        <div className={`h-full rounded-full transition-all duration-700 ${pct >= 100 ? 'bg-apple-green' : 'bg-apple-blue'}`}
          style={{ width: `${pct}%` }} />
      </div>
      {pct < 100 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          <Link to="/compass/retire" className="rounded-full border border-apple-gray-200 bg-white px-3 py-1.5 text-[11px] font-medium text-apple-gray-600 active:bg-apple-gray-100">
            +$100/mo → {money(plus100)} more
          </Link>
          <Link to="/compass/retire" className="rounded-full border border-apple-gray-200 bg-white px-3 py-1.5 text-[11px] font-medium text-apple-gray-600 active:bg-apple-gray-100">
            Retire 2 yrs later → {money(plus2yr)} more
          </Link>
        </div>
      )}
      <p className="mt-2 text-[10px] text-apple-gray-400">
        Uses your live portfolio value ({money(liveAssets)}) as the starting point. The picks below close your
        target-mix gaps — the engine that gets you there.
      </p>
    </section>
  )
}

function TargetsSheet({ slug, current, onClose, onSaved }: {
  slug: string; current: Record<string, number>; onClose: () => void; onSaved: () => void
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(TARGET_CLASSES.map(tc => [
      tc.key, String(current[tc.key] ?? tc.fallback),
    ]))
  )
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const total = TARGET_CLASSES.reduce((sum, tc) => sum + (parseFloat(values[tc.key]) || 0), 0)
  const valid = Math.abs(total - 100) <= 0.5

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setErr(null)
    try {
      await api.put(`/portfolio/${slug}/targets`, {
        targets: Object.fromEntries(TARGET_CLASSES.map(tc => [tc.key, parseFloat(values[tc.key]) || 0])),
      })
      onSaved()
    } catch (error: any) {
      setErr(error.response?.data?.detail || "Couldn't save your targets.")
      setSaving(false)
    }
  }

  return (
    <Sheet title="My target mix" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <p className="text-xs text-apple-gray-500">
          How you want your money divided, as percentages. They need to add up to 100.
        </p>
        {TARGET_CLASSES.map(tc => (
          <div key={tc.key} className="flex items-center justify-between gap-3">
            <label className="text-sm text-apple-gray-700">{tc.label}</label>
            <div className="flex items-center gap-1">
              <input value={values[tc.key]} onChange={e => setValues({ ...values, [tc.key]: e.target.value })}
                inputMode="decimal" className={`${inputCls} w-20 text-right`} />
              <span className="text-sm text-apple-gray-400">%</span>
            </div>
          </div>
        ))}
        <p className={`text-right text-xs font-medium tabular-nums ${valid ? 'text-green-600' : 'text-apple-orange'}`}>
          Total: {total.toFixed(0)}%{!valid && ' — needs to be 100%'}
        </p>
        {err && <p className="text-xs text-apple-red">{err}</p>}
        <button type="submit" disabled={saving || !valid} className={primaryBtn}>
          {saving ? 'Saving…' : 'Save targets'}
        </button>
      </form>
    </Sheet>
  )
}
