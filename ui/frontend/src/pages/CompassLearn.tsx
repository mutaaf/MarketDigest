// Compass — Learn: the family's growing knowledge map. Topics arrive from
// Ask suggestions or get added here; every topic can teach a kid or an adult.
import { FormEvent, useEffect, useState } from 'react'
import { ChevronDown, Plus, Trash2, Sparkles, Baby, User } from 'lucide-react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { inputCls, usePortfolioSelection } from '../components/compass/ui'

interface Topic {
  id: string
  term: string
  short: string
  body: string
  source: 'ai' | 'built-in'
  taught?: Record<string, string>
}

const BUILT_INS: Topic[] = [
  { id: 'etf', term: 'ETF (Exchange-Traded Fund)', short: 'One purchase, hundreds of companies', source: 'built-in',
    body: "An ETF is a basket of many investments you buy in a single share. Buying VOO, for example, makes you a part-owner of all 500 companies in the S&P 500 at once. It's the easiest way to be diversified without picking individual stocks." },
  { id: 'expense-ratio', term: 'Expense ratio', short: 'What a fund charges you each year', source: 'built-in',
    body: "The yearly fee a fund keeps, as a percentage of your money. An expense ratio of 0.03% means you pay $3 a year for every $10,000 invested — almost nothing. Above 0.50% ($50 per $10,000), you should expect something special in return. Low costs are one of the few things in investing you fully control." },
  { id: 'diversification', term: 'Diversification', short: "Don't put all your eggs in one basket", source: 'built-in',
    body: "Spreading your money across many companies, industries, and countries so no single bad event can sink you. If you own only tech stocks and tech has a bad year, your whole portfolio has a bad year. Compass's health check watches this for you." },
  { id: 'asset-allocation', term: 'Asset allocation', short: 'Your recipe: stocks, bonds, real estate', source: 'built-in',
    body: "How you divide money between types of investments. Stocks grow the most but swing the hardest; bonds are steadier but grow slowly. A common long-term recipe is mostly stocks with some bonds, shifting toward bonds as retirement gets closer. Your target mix on the Ideas page is exactly this." },
  { id: 'index-fund', term: 'Index fund', short: 'Own the whole market, cheaply', source: 'built-in',
    body: "A fund that simply owns everything in a market index (like the S&P 500) instead of paying someone to guess winners. Decades of evidence show most professionals fail to beat the index over time — which is why low-cost index funds are the default recommendation for long-term money." },
  { id: 'compound-growth', term: 'Compound growth', short: 'Earnings on your earnings', source: 'built-in',
    body: "When your money earns returns, and those returns start earning returns too. $10,000 growing 7% a year becomes about $76,000 in 30 years — you contributed nothing extra; time did the work. It's why starting early beats starting big." },
  { id: 'dividend', term: 'Dividend', short: 'Companies paying you to own them', source: 'built-in',
    body: "Some companies pay shareholders a slice of profits in cash a few times a year. A 3% dividend yield means roughly $300 a year per $10,000 invested, on top of any price growth. Funds like SCHD focus on dependable dividend payers." },
  { id: 'volatility', term: 'Volatility', short: 'How bumpy the ride is', source: 'built-in',
    body: "How much an investment's price swings around. High volatility isn't automatically bad — it's the price of higher long-term growth — but it matters if the swings would scare you into selling at the worst moment. Compass shows this as the risk level on funds." },
  { id: 'pe-ratio', term: 'P/E ratio', short: 'What you pay per dollar of profits', source: 'built-in',
    body: "Price divided by earnings. A P/E of 20 means you're paying $20 for every $1 of the company's annual profit. Lower can mean a bargain (or a business in trouble); higher usually means the market expects big growth. It's most useful comparing similar companies." },
  { id: 'four-percent-rule', term: 'The 4% rule', short: 'How much retirement money is enough', source: 'built-in',
    body: "A rule of thumb: if you withdraw about 4% of your savings the first year of retirement (adjusting for inflation after), your money has historically lasted 30+ years. Flip it around: you need roughly 25x your yearly spending saved. Compass's retirement page does this math for you." },
  { id: 'dollar-cost-averaging', term: 'Dollar-cost averaging', short: 'Invest steadily, ignore the drama', source: 'built-in',
    body: "Investing a fixed amount on a schedule — say $500 every month — no matter what the market is doing. You automatically buy more shares when prices are low and fewer when they're high, and you never have to guess the 'right' moment to invest." },
  { id: 'rebalancing', term: 'Rebalancing', short: 'Nudging your mix back to plan', source: 'built-in',
    body: "Over time, whatever grew fastest takes over your portfolio and drifts you away from your target mix. Rebalancing means selling a little of what's overweight (or directing new money to what's underweight) to get back to plan. Compass's Ideas page points new money at what's underweight, which rebalances you gently without selling." },
]

export default function CompassLearn() {
  const { selected } = usePortfolioSelection()
  const [saved, setSaved] = useState<Topic[]>([])
  const [open, setOpen] = useState<string | null>(null)
  const [newTerm, setNewTerm] = useState('')
  const [adding, setAdding] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!selected) return
    api.get<{ topics: Topic[] }>(`/portfolio/${selected}/learn`)
      .then(res => setSaved(res.data.topics))
      .catch(() => setSaved([]))
  }, [selected])

  const addTopic = async (e: FormEvent) => {
    e.preventDefault()
    if (!newTerm.trim() || !selected) return
    setAdding(true)
    setErr(null)
    try {
      const res = await api.post<Topic>(`/portfolio/${selected}/learn`, { term: newTerm.trim() }, { timeout: 60000 })
      setSaved(prev => [res.data, ...prev.filter(t => t.id !== res.data.id)])
      setNewTerm('')
      setOpen(res.data.id)
    } catch (error: any) {
      setErr(error.response?.data?.detail || "Couldn't add that topic right now.")
    } finally {
      setAdding(false)
    }
  }

  const removeTopic = async (tid: string) => {
    if (!selected) return
    setSaved(prev => prev.filter(t => t.id !== tid))
    api.delete(`/portfolio/${selected}/learn/${tid}`).catch(() => {})
  }

  return (
    <div className="space-y-4 pb-6">
      <div className="animate-fadeUp">
        <h1 className="text-lg font-bold text-apple-gray-800">Learn</h1>
        <p className="text-xs text-apple-gray-500">
          Your family's knowledge map — it grows as you use Compass.{' '}
          <Link to="/compass/ask" className="text-apple-blue">Ask Compass</Link> anything and save what you learn.
        </p>
      </div>

      <form onSubmit={addTopic} className="animate-fadeUp flex gap-2" style={{ animationDelay: '60ms' }}>
        <input value={newTerm} onChange={e => setNewTerm(e.target.value)}
          placeholder="Add a topic — e.g. Roth IRA, bear market…" className={inputCls} />
        <button type="submit" disabled={adding || !newTerm.trim() || !selected}
          className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl bg-apple-blue text-white active:opacity-80 disabled:opacity-40">
          {adding ? <span className="text-xs">…</span> : <Plus size={18} />}
        </button>
      </form>
      {err && <p className="text-xs text-apple-red">{err}</p>}

      {saved.length > 0 && (
        <section>
          <h2 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-apple-gray-400">
            <Sparkles size={12} /> Your topics
          </h2>
          <div className="space-y-2">
            {saved.map((t, i) => (
              <TopicCard key={t.id} topic={t} open={open === t.id} onToggle={() => setOpen(open === t.id ? null : t.id)}
                onRemove={() => removeTopic(t.id)} slug={selected} delay={i * 50} />
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-apple-gray-400">The basics</h2>
        <div className="space-y-2">
          {BUILT_INS.map((t, i) => (
            <TopicCard key={t.id} topic={t} open={open === t.id} onToggle={() => setOpen(open === t.id ? null : t.id)}
              slug={selected} delay={i * 30} />
          ))}
        </div>
      </section>
    </div>
  )
}

function TopicCard({ topic, open, onToggle, onRemove, slug, delay }: {
  topic: Topic; open: boolean; onToggle: () => void; onRemove?: () => void; slug: string; delay: number
}) {
  const [lesson, setLesson] = useState<{ audience: string; text: string } | null>(null)
  const [teaching, setTeaching] = useState<string | null>(null)

  const teach = async (audience: 'kid' | 'adult') => {
    if (lesson?.audience === audience) { setLesson(null); return }
    setTeaching(audience)
    try {
      const res = await api.post<{ text: string }>('/compass/teach',
        { term: topic.term, audience, portfolio: slug || null }, { timeout: 60000 })
      setLesson({ audience, text: res.data.text })
    } catch (error: any) {
      setLesson({ audience, text: error.response?.data?.detail || "Couldn't load the lesson — try again in a minute." })
    } finally {
      setTeaching(null)
    }
  }

  return (
    <div className="animate-fadeUp overflow-hidden rounded-2xl border border-apple-gray-200 bg-white" style={{ animationDelay: `${delay}ms` }}>
      <button onClick={onToggle}
        className="flex min-h-[56px] w-full items-center justify-between gap-3 px-4 py-3 text-left active:bg-apple-gray-50">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-apple-gray-800">
            {topic.term}
            {topic.source === 'ai' && <Sparkles size={11} className="ml-1.5 inline text-apple-blue" />}
          </p>
          {topic.short && <p className="truncate text-xs text-apple-gray-400">{topic.short}</p>}
        </div>
        <ChevronDown size={16} className={`shrink-0 text-apple-gray-300 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="border-t border-apple-gray-100 px-4 py-3">
          <p className="text-sm leading-relaxed text-apple-gray-600">{topic.body}</p>

          <div className="mt-3 flex items-center gap-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-apple-gray-400">Teach me:</span>
            <button onClick={() => teach('kid')}
              className={`flex min-h-[36px] items-center gap-1 rounded-full px-3 text-xs font-medium ${
                lesson?.audience === 'kid' ? 'bg-apple-blue text-white' : 'border border-apple-gray-200 bg-white text-apple-gray-600 active:bg-apple-gray-100'
              }`}>
              <Baby size={12} /> {teaching === 'kid' ? '…' : 'For a kid'}
            </button>
            <button onClick={() => teach('adult')}
              className={`flex min-h-[36px] items-center gap-1 rounded-full px-3 text-xs font-medium ${
                lesson?.audience === 'adult' ? 'bg-apple-blue text-white' : 'border border-apple-gray-200 bg-white text-apple-gray-600 active:bg-apple-gray-100'
              }`}>
              <User size={12} /> {teaching === 'adult' ? '…' : 'For an adult'}
            </button>
            {onRemove && (
              <button onClick={onRemove} title="Remove topic"
                className="ml-auto flex min-h-[36px] min-w-[36px] items-center justify-center text-apple-gray-300 active:text-apple-red">
                <Trash2 size={13} />
              </button>
            )}
          </div>

          {lesson && (
            <div className="animate-fadeUp mt-2 rounded-xl bg-apple-blue/5 p-3">
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-apple-gray-700">{lesson.text}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
