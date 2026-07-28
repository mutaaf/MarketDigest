// Shared Compass UI primitives — every data view gets explicit
// loading / empty / error / partial states (see docs/COMPASS_PLAN.md UX principles).
import { ReactNode, useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw, Info, X } from 'lucide-react'
import api from '../../api/client'
import { PortfolioListItem } from '../../api/compass-types'

const SELECTED_KEY = 'compass.selectedPortfolio'

export function gradeColor(grade: string | null | undefined): string {
  if (!grade) return 'bg-apple-gray-200 text-apple-gray-600'
  if (grade.startsWith('A')) return 'bg-apple-green/15 text-green-700'
  if (grade.startsWith('B')) return 'bg-apple-blue/10 text-apple-blue'
  if (grade.startsWith('C')) return 'bg-apple-yellow/20 text-yellow-700'
  if (grade.startsWith('D')) return 'bg-apple-orange/15 text-orange-700'
  return 'bg-apple-red/10 text-apple-red'
}

export function GradeChip({ grade, size = 'md' }: { grade: string | null | undefined; size?: 'md' | 'lg' }) {
  const sizeCls = size === 'lg'
    ? 'w-16 h-16 text-2xl rounded-2xl'
    : 'w-10 h-10 text-sm rounded-xl'
  return (
    <span className={`inline-flex items-center justify-center font-bold ${sizeCls} ${gradeColor(grade)}`}>
      {grade ?? '—'}
    </span>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-apple-gray-200/70 ${className}`} />
}

export function PageSkeleton() {
  return (
    <div className="space-y-4 p-1">
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-10 w-2/3" />
      <Skeleton className="h-20 w-full" />
      <Skeleton className="h-20 w-full" />
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="rounded-2xl border border-apple-red/20 bg-apple-red/5 p-5 text-center">
      <AlertTriangle className="mx-auto mb-2 text-apple-red" size={22} />
      <p className="text-sm text-apple-gray-700">
        {message || "Something went wrong loading this. Your data is safe."}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-white px-5 text-sm font-medium text-apple-gray-700 shadow-sm border border-apple-gray-200 active:bg-apple-gray-100"
        >
          <RefreshCw size={15} /> Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title, hint, action }: { title: string; hint: string; action?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-apple-gray-300 bg-white p-8 text-center">
      <p className="text-base font-semibold text-apple-gray-800">{title}</p>
      <p className="mx-auto mt-1 max-w-sm text-sm text-apple-gray-500">{hint}</p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  )
}

export function WarningsBanner({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null
  return (
    <div className="flex items-start gap-2 rounded-xl border border-apple-yellow/40 bg-apple-yellow/10 px-3 py-2.5">
      <Info size={16} className="mt-0.5 shrink-0 text-yellow-700" />
      <div className="text-xs leading-relaxed text-yellow-800">
        {warnings.map((w, i) => <p key={i}>{w}</p>)}
      </div>
    </div>
  )
}

export function AllocationBars({ slices, max = 8 }: { slices: { label: string; weight: number }[]; max?: number }) {
  const shown = slices.slice(0, max)
  if (!shown.length) {
    return <p className="text-sm text-apple-gray-400">Nothing to show yet.</p>
  }
  return (
    <div className="space-y-2.5">
      {shown.map(s => (
        <div key={s.label}>
          <div className="mb-1 flex items-baseline justify-between text-sm">
            <span className="text-apple-gray-700">{s.label}</span>
            <span className="font-medium tabular-nums text-apple-gray-800">{s.weight.toFixed(1)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-apple-gray-100">
            <div
              className="h-full rounded-full bg-apple-blue transition-all duration-500"
              style={{ width: `${Math.min(100, s.weight)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

export function money(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—'
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: n >= 1000 ? 0 : 2 })
}

export function signed(n: number | null | undefined, suffix = ''): string {
  if (n === null || n === undefined) return '—'
  return `${n >= 0 ? '+' : ''}${n.toLocaleString('en-US', { maximumFractionDigits: 2 })}${suffix}`
}

/** Bottom sheet on mobile, centered card on desktop.
 * z-[70] so it always covers the bottom tab bar (nav is z-50); body scrolls
 * inside the sheet when content is taller than the screen. */
export function Sheet({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-black/30 md:items-center" onClick={onClose}>
      <div
        className="flex max-h-[88dvh] w-full flex-col rounded-t-3xl bg-white shadow-xl md:max-h-[85vh] md:max-w-md md:rounded-3xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 pt-4">
          <h3 className="text-base font-semibold text-apple-gray-800">{title}</h3>
          <button onClick={onClose} className="flex min-h-[44px] min-w-[44px] items-center justify-center text-apple-gray-400"><X size={20} /></button>
        </div>
        <div
          className="overflow-y-auto px-5 pt-2"
          style={{ paddingBottom: 'max(1.25rem, env(safe-area-inset-bottom))' }}
        >
          {children}
        </div>
      </div>
    </div>
  )
}

export const inputCls = 'w-full min-h-[44px] rounded-xl border border-apple-gray-200 bg-apple-gray-50 px-3 text-sm text-apple-gray-800 focus:border-apple-blue focus:outline-none'
export const primaryBtn = 'w-full min-h-[48px] rounded-xl bg-apple-blue text-sm font-semibold text-white active:opacity-80 disabled:opacity-40'

/** Selected-portfolio state shared across Compass pages via localStorage.
 *
 * `selected` stays empty until the portfolio list has loaded and the stored
 * preference is validated against it — so pages never fetch with a slug that
 * points at a deleted portfolio (which used to leave a stuck 404 on devices
 * that remembered an old selection). */
export function usePortfolioSelection() {
  const [portfolios, setPortfolios] = useState<PortfolioListItem[] | null>(null)
  const [selected, setSelectedState] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const refresh = () => {
    setError(null)
    api.get<{ portfolios: PortfolioListItem[] }>('/portfolio/list')
      .then(res => {
        setPortfolios(res.data.portfolios)
        const slugs = res.data.portfolios.map(p => p.slug)
        const stored = localStorage.getItem(SELECTED_KEY) || ''
        setSelected(slugs.includes(stored) ? stored : (slugs[0] ?? ''))
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
  }

  const setSelected = (slug: string) => {
    localStorage.setItem(SELECTED_KEY, slug)
    setSelectedState(slug)
  }

  useEffect(refresh, [])
  return { portfolios, selected, setSelected, refresh, error }
}
