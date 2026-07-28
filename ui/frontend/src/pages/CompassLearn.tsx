// Compass — Learn: investing ideas explained like you'd explain them to a friend.
import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { Link } from 'react-router-dom'

const TOPICS: { term: string; short: string; body: string }[] = [
  {
    term: 'ETF (Exchange-Traded Fund)',
    short: 'One purchase, hundreds of companies',
    body: "An ETF is a basket of many investments you buy in a single share. Buying VOO, for example, makes you a part-owner of all 500 companies in the S&P 500 at once. It's the easiest way to be diversified without picking individual stocks.",
  },
  {
    term: 'Expense ratio',
    short: 'What a fund charges you each year',
    body: "The yearly fee a fund keeps, as a percentage of your money. An expense ratio of 0.03% means you pay $3 a year for every $10,000 invested — almost nothing. Above 0.50% ($50 per $10,000), you should expect something special in return. Low costs are one of the few things in investing you fully control.",
  },
  {
    term: 'Diversification',
    short: "Don't put all your eggs in one basket",
    body: "Spreading your money across many companies, industries, and countries so no single bad event can sink you. If you own only tech stocks and tech has a bad year, your whole portfolio has a bad year. Compass's health check watches this for you.",
  },
  {
    term: 'Asset allocation',
    short: 'Your recipe: stocks, bonds, real estate',
    body: "How you divide money between types of investments. Stocks grow the most but swing the hardest; bonds are steadier but grow slowly. A common long-term recipe is mostly stocks with some bonds, shifting toward bonds as retirement gets closer. Your target mix on the Ideas page is exactly this.",
  },
  {
    term: 'Index fund',
    short: 'Own the whole market, cheaply',
    body: "A fund that simply owns everything in a market index (like the S&P 500) instead of paying someone to guess winners. Decades of evidence show most professionals fail to beat the index over time — which is why low-cost index funds are the default recommendation for long-term money.",
  },
  {
    term: 'Compound growth',
    short: 'Earnings on your earnings',
    body: "When your money earns returns, and those returns start earning returns too. $10,000 growing 7% a year becomes about $76,000 in 30 years — you contributed nothing extra; time did the work. It's why starting early beats starting big.",
  },
  {
    term: 'Dividend',
    short: 'Companies paying you to own them',
    body: "Some companies pay shareholders a slice of profits in cash a few times a year. A 3% dividend yield means roughly $300 a year per $10,000 invested, on top of any price growth. Funds like SCHD focus on dependable dividend payers.",
  },
  {
    term: 'Volatility',
    short: 'How bumpy the ride is',
    body: "How much an investment's price swings around. High volatility isn't automatically bad — it's the price of higher long-term growth — but it matters if the swings would scare you into selling at the worst moment. Compass shows this as the risk level on funds.",
  },
  {
    term: 'P/E ratio',
    short: 'What you pay per dollar of profits',
    body: "Price divided by earnings. A P/E of 20 means you're paying $20 for every $1 of the company's annual profit. Lower can mean a bargain (or a business in trouble); higher usually means the market expects big growth. It's most useful comparing similar companies.",
  },
  {
    term: 'The 4% rule',
    short: 'How much retirement money is enough',
    body: "A rule of thumb: if you withdraw about 4% of your savings the first year of retirement (adjusting for inflation after), your money has historically lasted 30+ years. Flip it around: you need roughly 25x your yearly spending saved. Compass's retirement page does this math for you.",
  },
  {
    term: 'Dollar-cost averaging',
    short: 'Invest steadily, ignore the drama',
    body: "Investing a fixed amount on a schedule — say $500 every month — no matter what the market is doing. You automatically buy more shares when prices are low and fewer when they're high, and you never have to guess the 'right' moment to invest.",
  },
  {
    term: 'Rebalancing',
    short: 'Nudging your mix back to plan',
    body: "Over time, whatever grew fastest takes over your portfolio and drifts you away from your target mix. Rebalancing means selling a little of what's overweight (or directing new money to what's underweight) to get back to plan. Compass's Ideas page points new money at what's underweight, which rebalances you gently without selling.",
  },
]

export default function CompassLearn() {
  const [open, setOpen] = useState<string | null>(null)

  return (
    <div className="space-y-4 pb-6">
      <div>
        <h1 className="text-lg font-bold text-apple-gray-800">Learn</h1>
        <p className="text-xs text-apple-gray-500">
          The ideas behind good investing, minus the jargon. Want more?{' '}
          <Link to="/compass/ask" className="text-apple-blue">Ask Compass</Link> about anything.
        </p>
      </div>
      <div className="space-y-2">
        {TOPICS.map(t => {
          const isOpen = open === t.term
          return (
            <div key={t.term} className="overflow-hidden rounded-2xl border border-apple-gray-200 bg-white">
              <button
                onClick={() => setOpen(isOpen ? null : t.term)}
                className="flex min-h-[56px] w-full items-center justify-between gap-3 px-4 py-3 text-left active:bg-apple-gray-50"
              >
                <div>
                  <p className="text-sm font-semibold text-apple-gray-800">{t.term}</p>
                  <p className="text-xs text-apple-gray-400">{t.short}</p>
                </div>
                <ChevronDown size={16} className={`shrink-0 text-apple-gray-300 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
              </button>
              {isOpen && (
                <p className="border-t border-apple-gray-100 px-4 py-3 text-sm leading-relaxed text-apple-gray-600">
                  {t.body}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
