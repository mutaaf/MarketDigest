// Term — tap any piece of jargon, get a plain-English definition in place.
// Three cache layers: built-in glossary (instant, offline) -> localStorage
// (survives sessions) -> /compass/teach (LLM, server-cached). Definitions
// render inline below the text — no floating popovers to misplace on mobile.
import { ReactNode, createContext, useContext, useState } from 'react'
import { X } from 'lucide-react'

const GLOSSARY: Record<string, string> = {
  'beta': "How much an investment moves compared to the whole market. Beta 1 = moves with the market; 1.3 = swings 30% harder both ways; 0.5 = half the swings.",
  'expense ratio': "A fund's yearly fee, taken as a % of your money. 0.03% = $3 per $10,000 per year. One of the few costs you fully control — lower is better.",
  'dividend yield': "Cash paid to you yearly, as a % of the price. A 3% yield pays about $300/year per $10,000 invested, on top of any price change.",
  'dividends': "Cash some companies and funds pay their owners a few times a year — real money into your account, on top of any price growth.",
  'volatility': "How bumpy the ride is — how much the price swings. Higher volatility means bigger drops on bad days and bigger jumps on good ones.",
  'diversification': "Spreading money across many companies, industries, and countries so no single failure can sink you.",
  'asset allocation': "Your recipe: what % goes to stocks vs bonds vs real estate vs cash. It drives your risk and growth more than any single pick.",
  'cost basis': "What you originally paid per share. Compass compares it to today's price to show your gain or loss.",
  'p/e ratio': "Price ÷ yearly earnings. P/E 20 = paying $20 for each $1 of annual profit. Best for comparing similar companies.",
  'peg ratio': "P/E adjusted for growth. Under ~1 can mean you're getting growth cheaply; well over 2 means you're paying up for it.",
  'market cap': "A company's total price tag: share price × number of shares. Large caps ($10B+) are steadier; small caps swing more.",
  'index fund': "A fund that simply owns everything in a market index instead of picking winners. Cheap, diversified, and historically hard to beat.",
  'etf': "A basket of many investments you buy as one share. Instant diversification with one purchase.",
  'reit': "A fund of income-producing real estate. You collect rent-driven dividends without owning buildings.",
  'bond': "A loan you make to a government or company. Steadier than stocks, pays interest, cushions crashes — but grows slower.",
  '4% rule': "Withdraw ~4% of savings in year one of retirement (inflation-adjusted after) and history says it lasts 30+ years. Flip side: save ~25x yearly spending.",
  'monte carlo': "Running your plan through 1,000 simulated market histories — booms, crashes, and all — to see how often it survives. That's the 'chance it works' number.",
  'rebalancing': "Nudging your mix back to plan by adding to whatever fell behind. Compass does this gently by pointing new money at what's underweight.",
  'compound growth': "Earnings earning their own earnings. It's slow at first and unstoppable later — the reason starting early beats starting big.",
  'overlap': "When two funds (or a fund and a stock you own) hold the same companies — you're less diversified than your count of holdings suggests.",
  'inflation': "Prices rising over time, which quietly shrinks what a dollar buys. ~2.5%/year historically; investing is how you outrun it.",
  'crypto': "Digital assets like Bitcoin. Can rise fast and drop 50%+ in months — treat it as the spiciest slice of a portfolio, not the base.",
}

const DEFS_KEY = 'compass.defs.v2'

// Timestamped entries so the storage GC can evict least-recently-used defs
function loadLocal(term: string): string | null {
  try {
    const defs = JSON.parse(localStorage.getItem(DEFS_KEY) || '{}')
    const entry = defs[term]
    if (entry?.t) {
      entry.ts = Date.now()  // touch for LRU
      localStorage.setItem(DEFS_KEY, JSON.stringify(defs))
      return entry.t
    }
  } catch { /* fine */ }
  return null
}

function saveLocal(term: string, text: string) {
  try {
    const defs = JSON.parse(localStorage.getItem(DEFS_KEY) || '{}')
    defs[term] = { t: text, ts: Date.now() }
    localStorage.setItem(DEFS_KEY, JSON.stringify(defs))
  } catch { /* storage full — GC runs elsewhere */ }
}

// One definition open per page: context carries the setter down.
const TermCtx = createContext<{
  open: (term: string) => void
} | null>(null)

/** Wrap page content once; renders the active definition card at the point
 * of the DefinitionOutlet (or floating bottom bar if none placed). */
export function TermProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<string | null>(null)
  const [text, setText] = useState<string>('')
  const [loading, setLoading] = useState(false)

  const open = async (term: string) => {
    const key = term.toLowerCase()
    setActive(term)
    const builtin = GLOSSARY[key]
    if (builtin) { setText(builtin); return }
    const local = loadLocal(key)
    if (local) { setText(local); return }
    setLoading(true)
    setText('')
    try {
      const api = (await import('../../api/client')).default
      const res = await api.post<{ text: string }>('/compass/teach',
        { term, audience: 'adult' }, { timeout: 60000 })
      setText(res.data.text)
      saveLocal(key, res.data.text)
    } catch {
      setText("Couldn't load a definition right now — try the Learn tab.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <TermCtx.Provider value={{ open }}>
      {children}
      {active && (
        <div className="fixed inset-x-3 z-[80] animate-fadeUp rounded-2xl border border-apple-gray-200 bg-white p-4 shadow-xl md:left-auto md:right-6 md:w-96"
          style={{ bottom: 'calc(4.5rem + env(safe-area-inset-bottom, 0px))' }}>
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-semibold capitalize text-apple-gray-800">{active}</p>
            <button onClick={() => setActive(null)} className="-mr-1 -mt-1 flex min-h-[36px] min-w-[36px] items-center justify-center text-apple-gray-400">
              <X size={16} />
            </button>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-apple-gray-600">
            {loading ? 'Looking that up…' : text}
          </p>
        </div>
      )}
    </TermCtx.Provider>
  )
}

/** Tappable term: <Term t="expense ratio">expense ratio</Term> */
export function Term({ t, children }: { t: string; children?: ReactNode }) {
  const ctx = useContext(TermCtx)
  if (!ctx) return <>{children ?? t}</>
  return (
    <button onClick={() => ctx.open(t)}
      className="inline cursor-help border-b border-dotted border-apple-gray-400 text-inherit">
      {children ?? t}
    </button>
  )
}
