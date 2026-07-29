// Rules of thumb — classic investor heuristics computed with THEIR numbers.
// Tabbed card used on Ideas and Retirement.
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Lightbulb, MessageCircleQuestion } from 'lucide-react'
import { money } from './ui'

interface Props {
  invested: number
  cash: number
  stockPct: number | null      // % of portfolio in stocks (US + intl)
  age?: number | null
  monthlySpending?: number | null
  expectedReturnPct?: number | null
}

interface Rule {
  key: string
  tab: string
  title: string
  headline: string
  detail: string
  ask: string
}

export default function RulesOfThumb(props: Props) {
  const rules = buildRules(props)
  const [active, setActive] = useState(rules[0]?.key)
  const rule = rules.find(r => r.key === active) ?? rules[0]
  if (!rule) return null

  return (
    <section className="animate-fadeUp rounded-2xl border border-apple-gray-200 bg-white p-4">
      <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-apple-gray-700">
        <Lightbulb size={14} className="text-apple-yellow" /> Rules of thumb, with your numbers
      </h3>
      <div className="-mx-1 mb-3 flex gap-1.5 overflow-x-auto px-1 pb-1" style={{ scrollbarWidth: 'none' }}>
        {rules.map(r => (
          <button key={r.key} onClick={() => setActive(r.key)}
            className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-medium ${
              r.key === rule.key ? 'bg-apple-blue text-white' : 'border border-apple-gray-200 bg-white text-apple-gray-600'
            }`}>
            {r.tab}
          </button>
        ))}
      </div>
      <div key={rule.key} className="animate-fadeUp">
        <p className="text-xs font-medium uppercase tracking-wide text-apple-gray-400">{rule.title}</p>
        <p className="mt-1 text-xl font-bold text-apple-gray-800">{rule.headline}</p>
        <p className="mt-1 text-xs leading-relaxed text-apple-gray-500">{rule.detail}</p>
        <Link to={`/compass/ask?q=${encodeURIComponent(rule.ask)}`}
          className="mt-2 inline-flex min-h-[36px] items-center gap-1.5 rounded-full bg-apple-blue/5 px-3 text-xs font-medium text-apple-blue active:bg-apple-blue/10">
          <MessageCircleQuestion size={12} /> Dig into this
        </Link>
      </div>
    </section>
  )
}

function buildRules({ invested, cash, stockPct, age, monthlySpending, expectedReturnPct }: Props): Rule[] {
  const rules: Rule[] = []
  const ret = expectedReturnPct || 7
  const total = invested + cash

  if (total > 0) {
    const doubleYears = 72 / ret
    rules.push({
      key: 'r72', tab: 'Rule of 72', title: 'Rule of 72 — how fast money doubles',
      headline: `Doubles every ~${doubleYears.toFixed(0)} years`,
      detail: `Divide 72 by your return (${ret}%) to estimate doubling time. Your ${money(total)} becomes ~${money(total * 2)} in ${doubleYears.toFixed(0)} years and ~${money(total * 4)} in ${(doubleYears * 2).toFixed(0)} — without adding a dollar.`,
      ask: 'Explain the Rule of 72 using my portfolio numbers.',
    })
    rules.push({
      key: 'fourpct', tab: '4% rule', title: '4% rule — income your money could pay today',
      headline: `${money(Math.round(total * 0.04 / 12))}/month`,
      detail: `Withdrawing ~4% a year has historically lasted 30+ years. Your ${money(total)} could sustainably pay about ${money(Math.round(total * 0.04))} a year, starting now.`,
      ask: 'Explain the 4% rule and what it means for my portfolio today.',
    })
  }

  if (monthlySpending && monthlySpending > 0) {
    const target = monthlySpending * 12 * 25
    const pct = Math.min(100, total / target * 100)
    rules.push({
      key: 'x25', tab: '25x rule', title: '25x rule — your financial-freedom number',
      headline: `${money(target)} (you're ${pct.toFixed(0)}% there)`,
      detail: `To spend ${money(monthlySpending)}/month forever, you need about 25x your yearly spending. That's ${money(target)} — and you've built ${pct.toFixed(0)}% of it.`,
      ask: 'Explain the 25x financial independence rule with my numbers.',
    })
  }

  if (age && stockPct !== null) {
    const suggested = Math.max(20, Math.min(100, 110 - age))
    const diff = stockPct - suggested
    rules.push({
      key: 'r110', tab: '110 − age', title: '110 minus age — a stock/bond starting point',
      headline: `~${suggested}% stocks suggested · you're at ${stockPct.toFixed(0)}%`,
      detail: `A classic starting point: hold roughly (110 − your age)% in stocks. At ${age}, that's ~${suggested}%. You're ${Math.abs(diff) < 5 ? 'right about there' : diff > 0 ? `${diff.toFixed(0)} points more aggressive` : `${Math.abs(diff).toFixed(0)} points more cautious`} — a starting point, not a law.`,
      ask: 'Explain the 110-minus-age rule and whether my stock allocation fits my age.',
    })
  }

  if (monthlySpending && monthlySpending > 0) {
    const months = cash / monthlySpending
    rules.push({
      key: 'efund', tab: 'Safety net', title: 'Emergency fund — months your cash covers',
      headline: `${months.toFixed(1)} months of spending`,
      detail: `Most planners suggest keeping 3–6 months of spending in cash before investing aggressively. Your ${money(cash)} covers ${months.toFixed(1)} months at ${money(monthlySpending)}/month.${months < 3 ? ' Consider building this up first.' : ''}`,
      ask: 'How big should my emergency fund be, given my spending?',
    })
  }

  return rules
}
