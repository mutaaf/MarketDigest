// Compass — Retirement: am I on track?
import { FormEvent, useEffect, useState } from 'react'
import api from '../api/client'
import {
  EmptyState, ErrorState, PageSkeleton, inputCls, money, primaryBtn,
  usePortfolioSelection,
} from '../components/compass/ui'

interface Projection {
  years_to_retirement: number
  projected_at_retirement: number
  safe_monthly_withdrawal: number
  success_probability: number | null
  readiness: string | null
  path: { age: number; balance: number }[]
  assumptions: { expected_return_pct: number; inflation_pct: number; note: string }
}

interface PlanResponse {
  inputs: Record<string, number | null | undefined>
  projection: Projection | null
}

const FIELDS: { key: string; label: string; placeholder: string; hint?: string }[] = [
  { key: 'current_age', label: 'Your age', placeholder: '35' },
  { key: 'retire_age', label: 'Age you want to retire', placeholder: '65' },
  { key: 'current_assets', label: 'Invested so far ($)', placeholder: '58000' },
  { key: 'monthly_contribution', label: 'Adding each month ($)', placeholder: '1500' },
  { key: 'monthly_spending', label: 'Monthly spending in retirement ($)', placeholder: '5000', hint: "In today's dollars — what you'd want to live on." },
  { key: 'expected_return_pct', label: 'Expected yearly return (%)', placeholder: '7', hint: 'US stocks have averaged ~7-10% before inflation. 7% is a sensible default.' },
]

export default function CompassRetire() {
  const { portfolios, selected, error: listError, refresh: refreshList } = usePortfolioSelection()
  const [form, setForm] = useState<Record<string, string>>({})
  const [projection, setProjection] = useState<Projection | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!selected) return
    setLoading(true)
    setProjection(null)
    api.get<PlanResponse>(`/portfolio/${selected}/retirement`, { timeout: 60000 })
      .then(res => {
        const inputs = res.data.inputs || {}
        setForm(Object.fromEntries(
          Object.entries(inputs)
            .filter(([, v]) => v !== null && v !== undefined)
            .map(([k, v]) => [k, String(Math.round((v as number) * 100) / 100)])
        ))
        setProjection(res.data.projection)
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [selected])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const body: Record<string, number> = {}
      for (const f of FIELDS) {
        if (form[f.key]?.trim()) body[f.key] = parseFloat(form[f.key])
      }
      const res = await api.post<PlanResponse>(`/portfolio/${selected}/retirement`, body, { timeout: 60000 })
      setProjection(res.data.projection)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Couldn't run the projection. Check the numbers and try again.")
    } finally {
      setBusy(false)
    }
  }

  if (listError) return <ErrorState message={listError} onRetry={refreshList} />
  if (portfolios && portfolios.length === 0) {
    return <EmptyState title="No portfolio yet" hint="Create your portfolio on the Portfolio page first — then plan your retirement here." />
  }
  if (loading) return <PageSkeleton />

  const prob = projection?.success_probability ?? null
  const probColor = prob === null ? '' : prob >= 85 ? 'text-green-600' : prob >= 60 ? 'text-yellow-600' : 'text-apple-red'

  return (
    <div className="mx-auto max-w-3xl space-y-4 pb-6">
      <div>
        <h1 className="text-lg font-bold text-apple-gray-800">Retirement</h1>
        <p className="text-xs text-apple-gray-500">Am I on track? All numbers are in today's dollars.</p>
      </div>

      <form onSubmit={submit} className="rounded-2xl border border-apple-gray-200 bg-white p-4">
        <div className="grid grid-cols-2 gap-3">
          {FIELDS.map(f => (
            <div key={f.key} className={f.key === 'monthly_spending' || f.key === 'expected_return_pct' ? 'col-span-2 sm:col-span-1' : ''}>
              <label className="mb-1 block text-xs font-medium text-apple-gray-500">{f.label}</label>
              <input
                value={form[f.key] ?? ''}
                onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                placeholder={f.placeholder}
                inputMode="decimal"
                className={inputCls}
              />
              {f.hint && <p className="mt-1 text-[10px] leading-snug text-apple-gray-400">{f.hint}</p>}
            </div>
          ))}
        </div>
        {error && <p className="mt-3 text-xs text-apple-red">{error}</p>}
        <button type="submit" disabled={busy} className={`${primaryBtn} mt-4`}>
          {busy ? 'Calculating…' : projection ? 'Update my plan' : 'Am I on track?'}
        </button>
      </form>

      {projection && (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <ResultCard label={`Projected at ${form.retire_age || 'retirement'}`} value={money(projection.projected_at_retirement)} />
            <ResultCard label="Could safely spend" value={`${money(projection.safe_monthly_withdrawal)}/mo`} />
            <div className="rounded-2xl border border-apple-gray-200 bg-white p-4 text-center">
              <p className="text-[11px] font-medium uppercase tracking-wide text-apple-gray-400">Chance the plan works</p>
              <p className={`mt-1 text-2xl font-bold tabular-nums ${probColor}`}>
                {prob !== null ? `${prob.toFixed(0)}%` : '—'}
              </p>
              {prob === null && <p className="text-[10px] text-apple-gray-400">Add monthly spending to see this</p>}
            </div>
          </div>

          {projection.readiness && (
            <div className="rounded-2xl bg-apple-blue/5 p-4">
              <p className="text-sm leading-relaxed text-apple-gray-700">{projection.readiness}</p>
            </div>
          )}

          {/* Growth chart — CSS bars, oldest to retirement */}
          <div className="rounded-2xl border border-apple-gray-200 bg-white p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-apple-gray-400">How your money grows</p>
            <div className="flex h-36 items-end gap-[2px]">
              {projection.path.map(p => {
                const max = projection.path[projection.path.length - 1].balance || 1
                return (
                  <div key={p.age} className="group relative flex-1 rounded-t bg-apple-blue/70 transition-colors hover:bg-apple-blue"
                    style={{ height: `${Math.max(2, (p.balance / max) * 100)}%` }}
                    title={`Age ${p.age}: ${money(p.balance)}`} />
                )
              })}
            </div>
            <div className="mt-1 flex justify-between text-[10px] text-apple-gray-400">
              <span>Age {projection.path[0]?.age}</span>
              <span>Age {projection.path[projection.path.length - 1]?.age}</span>
            </div>
          </div>

          <p className="text-[11px] leading-relaxed text-apple-gray-400">{projection.assumptions.note}</p>
        </>
      )}
    </div>
  )
}

function ResultCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-apple-gray-200 bg-white p-4 text-center">
      <p className="text-[11px] font-medium uppercase tracking-wide text-apple-gray-400">{label}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums text-apple-gray-800">{value}</p>
    </div>
  )
}
