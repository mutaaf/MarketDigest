import { useState } from 'react'
import { Search } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import api from '../api/client'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ScoreCardDetail from '../components/common/ScoreCardDetail'
import type { ScoreCardSummary, ScoreCardFull } from '../api/scorecard-types'

const gradeColors: Record<string, { bg: string; text: string }> = {
  'A+': { bg: 'bg-green-500', text: 'text-white' },
  A:    { bg: 'bg-green-500', text: 'text-white' },
  'A-': { bg: 'bg-green-400', text: 'text-white' },
  'B+': { bg: 'bg-blue-500',  text: 'text-white' },
  B:    { bg: 'bg-blue-500',  text: 'text-white' },
  'B-': { bg: 'bg-blue-400',  text: 'text-white' },
  'C+': { bg: 'bg-yellow-500', text: 'text-white' },
  C:    { bg: 'bg-yellow-500', text: 'text-white' },
  'C-': { bg: 'bg-yellow-400', text: 'text-white' },
  D:    { bg: 'bg-orange-500', text: 'text-white' },
  F:    { bg: 'bg-red-500',    text: 'text-white' },
}

export default function ScoreCard() {
  const { data: cards, loading, error } = useApi<ScoreCardSummary[]>('/scorecard/all')
  const [selected, setSelected] = useState<string | null>(null)
  const [detail, setDetail] = useState<ScoreCardFull | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  // Search state
  const [searchTicker, setSearchTicker] = useState('')
  const [searchDetail, setSearchDetail] = useState<ScoreCardFull | null>(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  const selectCard = async (symbol: string) => {
    // Clear search result when selecting from grid
    setSearchDetail(null)
    setSearchError(null)
    if (selected === symbol) {
      setSelected(null)
      setDetail(null)
      return
    }
    setSelected(symbol)
    setDetail(null)
    setDetailLoading(true)
    try {
      const res = await api.get<ScoreCardFull>(`/scorecard/${symbol}`)
      setDetail(res.data)
    } catch {
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }

  const lookupTicker = async () => {
    const ticker = searchTicker.trim().toUpperCase()
    if (!ticker) return
    setSelected(null)
    setDetail(null)
    setSearchDetail(null)
    setSearchError(null)
    setSearchLoading(true)
    try {
      const res = await api.get<ScoreCardFull>(`/scorecard/${ticker}`)
      setSearchDetail(res.data)
    } catch {
      setSearchError(`No data available for ${ticker}`)
    } finally {
      setSearchLoading(false)
    }
  }

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto pb-24 md:pb-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-apple-gray-800">Score Cards</h1>
        <p className="text-sm text-apple-gray-400 mt-1">
          Technical scoring for all enabled instruments
        </p>
      </div>

      {/* Ticker search */}
      <div className="bg-white rounded-2xl border border-apple-gray-200 p-4 mb-6">
        <label className="text-sm font-medium text-apple-gray-700 block mb-2">Look up any ticker</label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-apple-gray-400" />
            <input
              type="text"
              value={searchTicker}
              onChange={e => setSearchTicker(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === 'Enter' && lookupTicker()}
              placeholder="e.g. AAPL, TSLA, MSFT"
              className="w-full pl-9 pr-3 py-2 border border-apple-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-apple-blue/20 focus:border-apple-blue"
            />
          </div>
          <button
            onClick={lookupTicker}
            disabled={!searchTicker.trim() || searchLoading}
            className="px-4 py-2 bg-apple-blue text-white text-sm font-medium rounded-xl hover:bg-blue-600 disabled:opacity-50 whitespace-nowrap"
          >
            {searchLoading ? 'Loading...' : 'Look Up'}
          </button>
        </div>
        {searchLoading && <div className="mt-3"><LoadingSpinner /></div>}
        {searchError && (
          <p className="mt-3 text-sm text-red-600">{searchError}</p>
        )}
        {searchDetail && (
          <div className="mt-4">
            <ScoreCardDetail card={searchDetail} />
          </div>
        )}
      </div>

      {loading && <LoadingSpinner />}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-sm text-red-700">
          Failed to load score cards: {error}
        </div>
      )}

      {!loading && cards && (
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Overview grid */}
          <div className="flex-1 min-w-0">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {cards.map(card => {
                const colors = gradeColors[card.grade] || { bg: 'bg-gray-500', text: 'text-white' }
                const isSelected = selected === card.symbol
                return (
                  <button
                    key={card.symbol}
                    onClick={() => selectCard(card.symbol)}
                    className={`bg-white rounded-2xl border p-4 text-left transition-all hover:shadow-md ${
                      isSelected ? 'border-apple-blue ring-2 ring-apple-blue/20' : 'border-apple-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className={`${colors.bg} ${colors.text} text-lg font-black w-10 h-10 rounded-xl flex items-center justify-center`}>
                        {card.grade}
                      </div>
                      <span className="text-lg font-bold text-apple-gray-800">{card.score}</span>
                    </div>
                    <p className="text-sm font-semibold text-apple-gray-800 truncate">{card.symbol}</p>
                    <p className="text-[11px] text-apple-gray-400 truncate">{card.name}</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-apple-gray-500">
                        {card.trend_emoji} {(card.trend || '').replace('_', ' ')}
                      </span>
                      {card.rsi != null && (
                        <span className="text-xs text-apple-gray-400">RSI {card.rsi.toFixed(0)}</span>
                      )}
                    </div>
                    {card.signals.length > 0 && (
                      <p className="text-[10px] text-apple-blue mt-1 truncate">{card.signals[0]}</p>
                    )}
                  </button>
                )
              })}
            </div>

            {cards.length === 0 && (
              <div className="text-center py-12 text-apple-gray-400 text-sm">
                No instruments could be scored. Check your instrument configuration.
              </div>
            )}
          </div>

          {/* Detail panel */}
          {selected && (
            <div className="lg:w-[400px] shrink-0">
              <div className="lg:sticky lg:top-6">
                {detailLoading && <LoadingSpinner />}
                {detail && <ScoreCardDetail card={detail} />}
                {!detailLoading && !detail && (
                  <div className="bg-white rounded-2xl border border-apple-gray-200 p-8 text-center text-sm text-apple-gray-400">
                    Failed to load detail for {selected}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
