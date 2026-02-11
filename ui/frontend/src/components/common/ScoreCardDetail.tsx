import type { ScoreCardFull } from '../../api/scorecard-types'

const gradeColors: Record<string, string> = {
  'A+': 'bg-green-500', A: 'bg-green-500', 'A-': 'bg-green-400',
  'B+': 'bg-blue-500', B: 'bg-blue-500', 'B-': 'bg-blue-400',
  'C+': 'bg-yellow-500', C: 'bg-yellow-500', 'C-': 'bg-yellow-400',
  D: 'bg-orange-500', F: 'bg-red-500',
}

function fmt(val: number | null | undefined, decimals = 2): string {
  if (val == null) return '-'
  return val.toFixed(decimals)
}

export default function ScoreCardDetail({ card }: { card: ScoreCardFull }) {
  const bgColor = gradeColors[card.grade] || 'bg-gray-500'

  return (
    <div className="space-y-4">
      {/* Grade + Setup */}
      <div className="bg-white rounded-2xl border border-apple-gray-200 p-5">
        <div className="flex items-start gap-4 mb-4">
          <div className={`${bgColor} text-white text-3xl font-black w-16 h-16 rounded-2xl flex items-center justify-center shrink-0`}>
            {card.grade}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-bold text-apple-gray-800">{card.symbol}</h3>
            <p className="text-sm text-apple-gray-500">{card.name}</p>
            <p className="text-xs text-apple-gray-400 mt-1">{card.verdict}</p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-2xl font-bold text-apple-gray-800">{card.score}</p>
            <p className="text-xs text-apple-gray-400">/ 100</p>
          </div>
        </div>

        {/* Score bar */}
        <div className="w-full h-2 bg-apple-gray-100 rounded-full overflow-hidden mb-4">
          <div className={`h-full ${bgColor} rounded-full transition-all`} style={{ width: `${Math.min(card.score, 100)}%` }} />
        </div>

        {/* Setup */}
        <div className="grid grid-cols-4 gap-3 text-center">
          <div>
            <p className="text-xs text-apple-gray-400">Entry</p>
            <p className="text-sm font-semibold text-apple-gray-800">${fmt(card.setup.entry)}</p>
          </div>
          <div>
            <p className="text-xs text-apple-gray-400">Target</p>
            <p className="text-sm font-semibold text-green-600">${fmt(card.setup.target)}</p>
          </div>
          <div>
            <p className="text-xs text-apple-gray-400">Stop</p>
            <p className="text-sm font-semibold text-red-600">${fmt(card.setup.stop)}</p>
          </div>
          <div>
            <p className="text-xs text-apple-gray-400">R:R</p>
            <p className="text-sm font-semibold text-apple-gray-800">{fmt(card.setup.risk_reward)}:1</p>
          </div>
        </div>

        {/* Signals */}
        {card.signals.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {card.signals.map((s, i) => (
              <span key={i} className="text-[11px] px-2 py-0.5 bg-apple-blue/10 text-apple-blue rounded-full font-medium">
                {s}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Technicals */}
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

      {/* Track Record */}
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
