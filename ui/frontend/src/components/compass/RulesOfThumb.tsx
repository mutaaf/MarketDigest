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
  monthlyContribution?: number | null
  expenseRatioPct?: number | null   // weighted fund cost, e.g. 0.05
  cryptoPct?: number | null         // % of portfolio in crypto
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

function buildRules({ invested, cash, stockPct, age, monthlySpending, expectedReturnPct,
                      monthlyContribution, expenseRatioPct, cryptoPct }: Props): Rule[] {
  const rules: Rule[] = []
  const ret = expectedReturnPct || 7
  const total = invested + cash
  const grow = (principal: number, monthly: number, years: number, ratePct: number) => {
    let b = principal
    for (let y = 0; y < years; y++) b = b * (1 + ratePct / 100) + monthly * 12
    return b
  }

  if (total > 0) {
    const doubleYears = 72 / ret
    rules.push({
      key: 'r72', tab: 'Rule of 72', title: 'Rule of 72 — how fast money doubles',
      headline: `Doubles every ~${doubleYears.toFixed(0)} years`,
      detail: `Divide 72 by your return (${ret}%) to estimate doubling time. Your ${money(total)} becomes ~${money(total * 2)} in ${doubleYears.toFixed(0)} years and ~${money(total * 4)} in ${(doubleYears * 2).toFixed(0)} — without adding a dollar.`,
      ask: 'Explain the Rule of 72 using my portfolio numbers.',
    })
    rules.push({
      key: 'r114', tab: '3x & 4x', title: 'Rules of 114 & 144 — tripling and quadrupling',
      headline: `3x in ~${(114 / ret).toFixed(0)} yrs · 4x in ~${(144 / ret).toFixed(0)} yrs`,
      detail: `Cousins of the Rule of 72: divide 114 by your return for tripling time, 144 for quadrupling. Your ${money(total)} → ~${money(total * 3)} in ${(114 / ret).toFixed(0)} years, ~${money(total * 4)} in ${(144 / ret).toFixed(0)}.`,
      ask: 'Explain the rules of 114 and 144 with my numbers.',
    })
    const horizon = age ? Math.max(10, Math.min(40, 65 - age)) : 25
    const contrib = monthlyContribution ?? 0
    const startNow = grow(total, contrib, horizon, ret)
    const startLater = grow(total, contrib, Math.max(0, horizon - 5), ret)
    if (startNow - startLater > 0) {
      rules.push({
        key: 'wait', tab: 'Cost of waiting', title: 'Time in the market — the cost of waiting 5 years',
        headline: `Waiting costs ~${money(Math.round(startNow - startLater))}`,
        detail: `The same money and habits started 5 years later ends ${money(Math.round(startNow - startLater))} smaller over your ${horizon}-year horizon. The best day to start was yesterday; the second best is today.`,
        ask: 'Show me why starting to invest earlier matters so much, using my numbers.',
      })
    }
    if (expenseRatioPct != null && expenseRatioPct > 0) {
      const drag = grow(total, contrib, 30, ret) - grow(total, contrib, 30, ret - expenseRatioPct)
      rules.push({
        key: 'fees', tab: 'Fee drag', title: 'The 1% rule — what fund fees really cost',
        headline: `Your ${expenseRatioPct.toFixed(2)}%/yr costs ~${money(Math.round(drag))} over 30 yrs`,
        detail: `Fees compound against you exactly like returns compound for you. At your funds' weighted ${expenseRatioPct.toFixed(2)}%/yr, that's ~${money(Math.round(drag))} of growth lost over 30 years${expenseRatioPct <= 0.1 ? " — happily, yours are already rock-bottom." : '. A 1%/yr fund would take several times more — this is why Compass grades cost.'}`,
        ask: 'How much do fund fees really cost over decades, using my portfolio?',
      })
    }
  }

  if (total > 0) {
    rules.push({
      key: 'fourpct', tab: '4% rule', title: '4% rule — income your money could pay today',
      headline: `${money(Math.round(total * 0.04 / 12))}/month`,
      detail: `Withdrawing ~4% a year has historically lasted 30+ years. Your ${money(total)} could sustainably pay about ${money(Math.round(total * 0.04))} a year, starting now.`,
      ask: 'Explain the 4% rule and what it means for my portfolio today.',
    })
  }

  if (cash > 0) {
    const halveYears = 70 / 2.5
    rules.push({
      key: 'infl', tab: 'Inflation', title: 'Rule of 70 — inflation quietly halves idle cash',
      headline: `Cash halves in buying power in ~${halveYears.toFixed(0)} yrs`,
      detail: `Divide 70 by inflation (~2.5%) to see how fast prices double — meaning your ${money(cash)} cash buys half as much in ~${halveYears.toFixed(0)} years if it just sits. Some cash is a safety net; the rest is why investing exists.`,
      ask: 'Explain how inflation erodes cash and how much of mine should be invested.',
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

  if (cryptoPct != null && cryptoPct > 0) {
    rules.push({
      key: 'crypto5', tab: '5% crypto', title: '5% crypto guideline — spice, not the meal',
      headline: `You're at ${cryptoPct.toFixed(0)}% crypto · guideline ≤5%`,
      detail: cryptoPct <= 5
        ? `A common guideline caps crypto at ~5% of a portfolio: big enough to matter if it soars, small enough that a 70% crash barely dents your plan. At ${cryptoPct.toFixed(0)}%, you're within it.`
        : `A common guideline caps crypto at ~5% of a portfolio — at ${cryptoPct.toFixed(0)}%, a typical crypto crash (50-70% happens regularly) would take a real bite out of your total. Worth a conscious decision rather than drift.`,
      ask: 'How much crypto is reasonable in my portfolio?',
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
