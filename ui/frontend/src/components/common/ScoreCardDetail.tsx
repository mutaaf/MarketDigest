import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ScoreCardFull, IndicatorAnalysis, TimeframeTargetExtended, Fundamentals } from '../../api/scorecard-types'

const gradeColors: Record<string, string> = {
  'A+': 'bg-green-500', A: 'bg-green-500', 'A-': 'bg-green-400',
  'B+': 'bg-blue-500', B: 'bg-blue-500', 'B-': 'bg-blue-400',
  'C+': 'bg-yellow-500', C: 'bg-yellow-500', 'C-': 'bg-yellow-400',
  D: 'bg-orange-500', F: 'bg-red-500',
}

const scoreBadgeColor = (score: number): string => {
  if (score >= 80) return 'bg-green-100 text-green-700'
  if (score >= 60) return 'bg-blue-100 text-blue-700'
  if (score >= 40) return 'bg-yellow-100 text-yellow-700'
  if (score >= 20) return 'bg-orange-100 text-orange-700'
  return 'bg-red-100 text-red-700'
}

function fmt(val: number | null | undefined, decimals = 2): string {
  if (val == null) return '-'
  return val.toFixed(decimals)
}

function fmtLarge(val: number | null | undefined): string {
  if (val == null) return '-'
  const abs = Math.abs(val)
  if (abs >= 1e12) return `$${(val / 1e12).toFixed(1)}T`
  if (abs >= 1e9) return `$${(val / 1e9).toFixed(1)}B`
  if (abs >= 1e6) return `$${(val / 1e6).toFixed(1)}M`
  if (abs >= 1e3) return `$${(val / 1e3).toFixed(1)}K`
  return `$${val.toFixed(0)}`
}

type TimeframeKey = 'daytrade' | 'swing' | 'longterm'

const TF_LABELS: Record<TimeframeKey, string> = {
  daytrade: 'Day Trade',
  swing: 'Swing',
  longterm: 'Long Term',
}

export default function ScoreCardDetail({ card }: { card: ScoreCardFull }) {
  const navigate = useNavigate()
  const hasMultiTf = !!card.multi_tf_scores
  const [selectedTf, setSelectedTf] = useState<TimeframeKey>('daytrade')
  const isEquity = !!card.fundamentals || !card.symbol.includes('=')

  const currentTfScore = hasMultiTf
    ? card.multi_tf_scores![selectedTf]
    : { score: card.score, grade: card.grade, signals: card.signals, verdict: card.verdict }

  const currentTfTarget = card.multi_tf_targets
    ? selectedTf === 'daytrade'
      ? card.multi_tf_targets.daily
      : selectedTf === 'swing'
        ? card.multi_tf_targets.swing
        : card.multi_tf_targets.longterm
    : null

  const displayGrade = currentTfScore?.grade || card.grade
  const displayScore = currentTfScore?.score ?? card.score
  const displayVerdict = currentTfScore?.verdict || card.verdict
  const bgColor = gradeColors[displayGrade] || 'bg-gray-500'

  return (
    <div className="space-y-4">
      {/* 1. Multi-Timeframe Score Tabs + Grade */}
      <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
        {/* Timeframe tabs */}
        {hasMultiTf && (
          <div className="flex gap-1.5 mb-4">
            {(Object.keys(TF_LABELS) as TimeframeKey[]).map(tf => {
              const tfData = card.multi_tf_scores![tf]
              const available = tf === 'daytrade' || tfData != null
              return (
                <button
                  key={tf}
                  onClick={() => available && setSelectedTf(tf)}
                  disabled={!available}
                  className={`flex-1 py-2 px-2 rounded-xl text-xs font-semibold transition-all ${
                    selectedTf === tf
                      ? 'bg-apple-blue text-white shadow-sm'
                      : available
                        ? 'bg-apple-gray-50 text-apple-gray-600 hover:bg-apple-gray-100'
                        : 'bg-apple-gray-50 text-apple-gray-300 cursor-not-allowed'
                  }`}
                >
                  {TF_LABELS[tf]}
                  {tfData && (
                    <span className="ml-1 opacity-75">{tfData.grade}</span>
                  )}
                  {tf === 'daytrade' && !tfData && (
                    <span className="ml-1 opacity-75">{card.grade}</span>
                  )}
                </button>
              )
            })}
          </div>
        )}

        <div className="flex items-start gap-4 mb-4">
          <div className={`${bgColor} text-white text-3xl font-black w-16 h-16 rounded-2xl flex items-center justify-center shrink-0`}>
            {displayGrade}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-bold text-apple-gray-800">{card.symbol}</h3>
            <p className="text-sm text-apple-gray-500">{card.name}</p>
            <p className="text-xs text-apple-gray-400 mt-1">{displayVerdict}</p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-2xl font-bold text-apple-gray-800">{displayScore.toFixed(0)}</p>
            <p className="text-xs text-apple-gray-400">/ 100</p>
          </div>
        </div>

        {/* Options Flow link */}
        {isEquity && (
          <button
            onClick={() => navigate(`/options?symbol=${card.symbol}`)}
            className="text-[11px] text-apple-blue hover:underline font-medium mb-3"
          >
            View Options Flow &rarr;
          </button>
        )}

        {/* Score bar */}
        <div className="w-full h-2 bg-apple-gray-100 rounded-full overflow-hidden mb-4">
          <div className={`h-full ${bgColor} rounded-full transition-all`} style={{ width: `${Math.min(displayScore, 100)}%` }} />
        </div>

        {/* Signals */}
        {currentTfScore && currentTfScore.signals.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {currentTfScore.signals.map((s, i) => (
              <span key={i} className="text-[11px] px-2 py-0.5 bg-apple-blue/10 text-apple-blue rounded-full font-medium">
                {s}
              </span>
            ))}
          </div>
        )}

        {/* Setup for selected timeframe */}
        {selectedTf === 'daytrade' ? (
          <div className="grid grid-cols-4 gap-3 text-center">
            <div>
              <p className="text-xs text-apple-gray-400">Entry</p>
              <p className="text-sm font-semibold text-apple-gray-800">${fmt(card.setup.entry)}</p>
            </div>
            <div>
              <p className="text-xs text-apple-gray-400">
                Target{card.setup.target_level ? ` (${card.setup.target_level})` : ''}
              </p>
              <p className="text-sm font-semibold text-green-600">${fmt(card.setup.target)}</p>
            </div>
            <div>
              <p className="text-xs text-apple-gray-400">
                Stop{card.setup.stop_level ? ` (${card.setup.stop_level})` : ''}
              </p>
              <p className="text-sm font-semibold text-red-600">${fmt(card.setup.stop)}</p>
            </div>
            <div>
              <p className="text-xs text-apple-gray-400">R:R</p>
              <p className="text-sm font-semibold text-apple-gray-800">{fmt(card.setup.risk_reward)}:1</p>
            </div>
          </div>
        ) : currentTfTarget ? (
          <div className="grid grid-cols-4 gap-3 text-center">
            <div>
              <p className="text-xs text-apple-gray-400">Entry</p>
              <p className="text-sm font-semibold text-apple-gray-800">${fmt(currentTfTarget.entry)}</p>
            </div>
            <div>
              <p className="text-xs text-apple-gray-400">
                Target{currentTfTarget.target_level ? ` (${currentTfTarget.target_level})` : ''}
              </p>
              <p className="text-sm font-semibold text-green-600">${fmt(currentTfTarget.target)}</p>
            </div>
            <div>
              <p className="text-xs text-apple-gray-400">
                Stop{currentTfTarget.stop_level ? ` (${currentTfTarget.stop_level})` : ''}
              </p>
              <p className="text-sm font-semibold text-red-600">${fmt(currentTfTarget.stop)}</p>
            </div>
            <div>
              <p className="text-xs text-apple-gray-400">R:R</p>
              <p className="text-sm font-semibold text-apple-gray-800">{fmt(currentTfTarget.risk_reward)}:1</p>
            </div>
          </div>
        ) : (
          <p className="text-xs text-apple-gray-400 text-center py-2">
            {TF_LABELS[selectedTf]} targets unavailable (insufficient data)
          </p>
        )}
      </div>

      {/* 2. Support/Resistance Zones */}
      {currentTfTarget && ((currentTfTarget as TimeframeTargetExtended).support_zones?.length > 0 ||
        (currentTfTarget as TimeframeTargetExtended).resistance_zones?.length > 0) && (
        <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
          <h4 className="text-sm font-semibold text-apple-gray-700 mb-3">Support & Resistance Zones</h4>
          <div className="flex flex-wrap gap-1.5 mb-2">
            {(currentTfTarget as TimeframeTargetExtended).resistance_zones?.map((r, i) => (
              <span key={`r-${i}`} className="text-[11px] px-2 py-0.5 bg-red-50 text-red-600 rounded-full font-medium">
                R: ${fmt(r)}
              </span>
            ))}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(currentTfTarget as TimeframeTargetExtended).support_zones?.map((s, i) => (
              <span key={`s-${i}`} className="text-[11px] px-2 py-0.5 bg-green-50 text-green-600 rounded-full font-medium">
                S: ${fmt(s)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 3. Fundamentals (equities only) */}
      {card.fundamentals && <FundamentalsCard fundamentals={card.fundamentals} />}

      {/* 4. Indicator Analysis */}
      {card.indicator_analyses && card.indicator_analyses.length > 0 && (
        <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
          <h4 className="text-sm font-semibold text-apple-gray-700 mb-3">Indicator Analysis</h4>
          <div className="space-y-2">
            {card.indicator_analyses.map((ia) => (
              <IndicatorAccordion key={ia.key} analysis={ia} />
            ))}
          </div>
        </div>
      )}

      {/* 5. Technicals (compact reference) */}
      <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
        <h4 className="text-sm font-semibold text-apple-gray-700 mb-3">Technicals</h4>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
          <TechRow label="RSI" value={card.technicals.rsi != null ? `${fmt(card.technicals.rsi, 1)} (${card.technicals.rsi_label})` : '-'} />
          <TechRow label="SMA 20" value={fmt(card.technicals.sma_20, 4)} />
          <TechRow label="SMA 50" value={fmt(card.technicals.sma_50, 4)} />
          <TechRow label="EMA 12" value={fmt(card.technicals.ema_12, 4)} />
          <TechRow label="EMA 26" value={fmt(card.technicals.ema_26, 4)} />
          <TechRow label="ATR" value={fmt(card.technicals.atr, 4)} />
          <TechRow label="Pivot R1" value={fmt(card.technicals.pivots?.r1, 4)} />
          <TechRow label="Pivot P" value={fmt(card.technicals.pivots?.pivot, 4)} />
          <TechRow label="Pivot S1" value={fmt(card.technicals.pivots?.s1, 4)} />
          <TechRow label="Volume Ratio" value={card.technicals.volume_ratio != null ? `${fmt(card.technicals.volume_ratio)}x` : '-'} />
          <TechRow label="Gap %" value={card.technicals.gap_pct != null ? `${fmt(card.technicals.gap_pct, 2)}%` : '-'} />
          <TechRow label="Trend" value={`${card.trend_emoji} ${(card.trend || 'neutral').replace('_', ' ')}`} />
        </div>
      </div>

      {/* 6. Track Record */}
      <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
        <h4 className="text-sm font-semibold text-apple-gray-700 mb-3">Track Record</h4>
        {card.history.appearances === 0 ? (
          <p className="text-xs text-apple-gray-400 text-center py-4">No graded history for this instrument yet.</p>
        ) : (
          <>
            <div className="grid grid-cols-3 md:grid-cols-5 gap-3 text-center mb-4">
              <MiniStat label="Appearances" value={String(card.history.appearances)} />
              <MiniStat label="Wins" value={String(card.history.wins)} color="text-green-600" />
              <MiniStat label="Losses" value={String(card.history.losses)} color="text-red-600" />
              <MiniStat label="Win Rate" value={card.history.win_rate != null ? `${card.history.win_rate}%` : '-'} />
              <MiniStat label="Avg R" value={card.history.avg_r != null ? `${card.history.avg_r}R` : '-'} />
            </div>

            {card.history.recent.length > 0 && (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-apple-gray-400">
                    <th className="text-left pb-2">Date</th>
                    <th className="text-left pb-2">Outcome</th>
                    <th className="text-right pb-2">Entry</th>
                    <th className="text-right pb-2">Return</th>
                    <th className="text-right pb-2">R</th>
                  </tr>
                </thead>
                <tbody>
                  {card.history.recent.map((r, i) => (
                    <tr key={i} className="border-t border-apple-gray-100">
                      <td className="py-1.5 text-apple-gray-600">{r.date}</td>
                      <td className="py-1.5">
                        <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                          r.outcome === 'win' ? 'bg-green-100 text-green-700' :
                          r.outcome === 'loss' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {r.outcome}
                        </span>
                      </td>
                      <td className="py-1.5 text-right text-apple-gray-600">{r.entry != null ? `$${fmt(r.entry)}` : '-'}</td>
                      <td className={`py-1.5 text-right font-medium ${(r.actual_return_pct ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {r.actual_return_pct != null ? `${r.actual_return_pct > 0 ? '+' : ''}${r.actual_return_pct}%` : '-'}
                      </td>
                      <td className={`py-1.5 text-right font-medium ${(r.r_multiple ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {r.r_multiple != null ? `${r.r_multiple > 0 ? '+' : ''}${r.r_multiple}R` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>
    </div>
  )
}

/* ── Sub-components ─────────────────────────────────────────── */

function FundamentalsCard({ fundamentals }: { fundamentals: Fundamentals }) {
  const [expanded, setExpanded] = useState(false)
  const scores = fundamentals.scores
  const metrics = fundamentals.metrics
  const compositeColor = scoreBadgeColor(scores.composite)

  return (
    <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-apple-gray-700">Fundamentals</h4>
        <div className="flex items-center gap-2">
          {fundamentals.sector && (
            <span className="text-[10px] px-2 py-0.5 bg-purple-50 text-purple-600 rounded-full">
              {fundamentals.sector}
            </span>
          )}
          <span className={`text-xs font-bold px-2 py-0.5 rounded-lg ${compositeColor}`}>
            {scores.composite.toFixed(0)}
          </span>
        </div>
      </div>

      {/* Sub-score bars */}
      <div className="space-y-2 mb-4">
        <ScoreBar label="Valuation" score={scores.valuation} />
        <ScoreBar label="Profitability" score={scores.profitability} />
        <ScoreBar label="Growth" score={scores.growth} />
        <ScoreBar label="Health" score={scores.health} />
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs mb-3">
        <MetricRow label="P/E" value={metrics.pe_ratio} fmt="ratio" />
        <MetricRow label="Fwd P/E" value={metrics.forward_pe} fmt="ratio" />
        <MetricRow label="P/B" value={metrics.pb_ratio} fmt="ratio" />
        <MetricRow label="EV/EBITDA" value={metrics.ev_ebitda} fmt="ratio" />
        <MetricRow label="D/E" value={metrics.debt_equity} fmt="ratio" />
        <MetricRow label="Current Ratio" value={metrics.current_ratio} fmt="ratio" />
        <MetricRow label="Gross Margin" value={metrics.gross_margin} fmt="pct" />
        <MetricRow label="Op Margin" value={metrics.operating_margin} fmt="pct" />
        <MetricRow label="Net Margin" value={metrics.net_margin} fmt="pct" />
        <MetricRow label="ROE" value={metrics.roe} fmt="pct" />
        <MetricRow label="ROA" value={metrics.roa} fmt="pct" />
        <MetricRow label="Rev Growth" value={metrics.revenue_growth} fmt="pct" />
        <MetricRow label="EPS Growth" value={metrics.eps_growth} fmt="pct" />
        <MetricRow label="Market Cap" value={fundamentals.market_cap} fmt="large" />
      </div>

      {/* Collapsible highlights */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-[11px] text-apple-blue hover:underline"
      >
        {expanded ? 'Hide' : 'Show'} financial highlights
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 text-xs">
          <HighlightSection title="Income" data={fundamentals.highlights.income} />
          <HighlightSection title="Balance Sheet" data={fundamentals.highlights.balance} />
          <HighlightSection title="Cash Flow" data={fundamentals.highlights.cashflow} />
        </div>
      )}
    </div>
  )
}

function ScoreBar({ label, score }: { label: string; score: number | null }) {
  if (score == null) return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-apple-gray-500 w-20">{label}</span>
      <span className="text-[10px] text-apple-gray-300">N/A</span>
    </div>
  )

  const color = score >= 70 ? 'bg-green-400' : score >= 50 ? 'bg-blue-400' : score >= 30 ? 'bg-yellow-400' : 'bg-red-400'

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-apple-gray-500 w-20 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-apple-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
      <span className="text-[10px] font-medium text-apple-gray-600 w-8 text-right">{score.toFixed(0)}</span>
    </div>
  )
}

function MetricRow({ label, value, fmt: fmtType }: { label: string; value: number | null; fmt: 'ratio' | 'pct' | 'large' }) {
  let display = '-'
  if (value != null) {
    if (fmtType === 'pct') display = `${value.toFixed(1)}%`
    else if (fmtType === 'large') display = fmtLarge(value)
    else display = value.toFixed(2)
  }

  return (
    <div className="flex justify-between py-0.5 border-b border-apple-gray-50">
      <span className="text-apple-gray-500">{label}</span>
      <span className="font-medium text-apple-gray-800">{display}</span>
    </div>
  )
}

function HighlightSection({ title, data }: { title: string; data: Record<string, number | null> }) {
  return (
    <div>
      <p className="text-[10px] font-semibold text-apple-gray-500 uppercase tracking-wide mb-1">{title}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
        {Object.entries(data).map(([key, val]) => (
          <div key={key} className="flex justify-between">
            <span className="text-apple-gray-500 capitalize">{key.replace(/_/g, ' ')}</span>
            <span className="font-medium text-apple-gray-800">{val != null ? fmtLarge(val) : '-'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function IndicatorAccordion({ analysis }: { analysis: IndicatorAnalysis }) {
  const [open, setOpen] = useState(false)
  const badgeClass = scoreBadgeColor(analysis.score)

  return (
    <div className="border border-apple-gray-100 rounded-xl overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left hover:bg-apple-gray-50 transition-colors"
      >
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${badgeClass} min-w-[32px] text-center`}>
          {analysis.score}
        </span>
        <div className="flex-1 min-w-0">
          <span className="text-xs font-semibold text-apple-gray-800">{analysis.name}</span>
          <span className="text-[10px] text-apple-gray-400 ml-2">{analysis.value_display}</span>
        </div>
        <span className="text-[10px] text-apple-gray-400">{analysis.weight_pct}%</span>
        <span className={`text-[10px] font-medium ${badgeClass.replace('bg-', 'text-').replace('-100', '-600')}`}>
          {analysis.score_label}
        </span>
        <svg
          className={`w-3.5 h-3.5 text-apple-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expandable body */}
      {open && (
        <div className="px-3 pb-3 space-y-2.5 border-t border-apple-gray-50">
          <AnalysisSection title="What It Measures" text={analysis.what_it_measures} />
          <AnalysisSection title="Current Reading" text={analysis.current_reading} />
          <AnalysisSection title="Why It Matters" text={analysis.why_it_matters} />
          <AnalysisSection title="Score Breakdown" text={analysis.score_explanation} />
          <AnalysisSection title="Trading Insight" text={analysis.trading_insight} />
        </div>
      )}
    </div>
  )
}

function AnalysisSection({ title, text }: { title: string; text: string }) {
  return (
    <div className="pt-2">
      <p className="text-[10px] font-semibold text-apple-gray-500 uppercase tracking-wide mb-0.5">{title}</p>
      <p className="text-xs text-apple-gray-700 leading-relaxed">{text}</p>
    </div>
  )
}

function TechRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1 border-b border-apple-gray-50">
      <span className="text-apple-gray-500">{label}</span>
      <span className="font-medium text-apple-gray-800">{value}</span>
    </div>
  )
}

function MiniStat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <p className="text-[10px] text-apple-gray-400">{label}</p>
      <p className={`text-sm font-bold ${color || 'text-apple-gray-800'}`}>{value}</p>
    </div>
  )
}
