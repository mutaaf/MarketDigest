import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { DigestSection } from './digestParser'

interface DigestCardProps {
  section: DigestSection
}

const QUICK_TAKE_TITLES = ['QUICK TAKE', 'QUICK-TAKE']

/** Color-coded prefix mapping for Quick Take lines */
const PREFIX_COLORS: Record<string, string> = {
  'Bullish:': 'text-green-600',
  'Bearish:': 'text-red-600',
  'Event:': 'text-blue-600',
  'Data:': 'text-blue-600',
  'Earnings:': 'text-purple-600',
}

function isQuickTake(title: string): boolean {
  return QUICK_TAKE_TITLES.some(qt => title.toUpperCase().includes(qt))
}

/** Render Quick Take content with color-coded prefix lines */
function QuickTakeContent({ html }: { html: string }) {
  // Parse lines from the HTML — each line is "  <b>Prefix:</b> rest" or plain text
  const div = document.createElement('div')
  div.innerHTML = html
  const text = div.textContent || div.innerText || ''
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean)

  return (
    <div className="digest-quick-take">
      {lines.map((line, i) => {
        let colorClass = 'text-apple-gray-800'
        let prefix = ''
        let rest = line

        for (const [p, cls] of Object.entries(PREFIX_COLORS)) {
          if (line.startsWith(p)) {
            colorClass = cls
            prefix = p
            rest = line.substring(p.length).trim()
            break
          }
        }

        return (
          <div key={i} className="digest-quick-take-line">
            {prefix && <span className={`font-semibold ${colorClass}`}>{prefix}</span>}
            <span className="text-apple-gray-700">{rest}</span>
          </div>
        )
      })}
    </div>
  )
}

export default function DigestCard({ section }: DigestCardProps) {
  const [expanded, setExpanded] = useState(true)
  const quickTake = isQuickTake(section.title)

  return (
    <div className={`card ${quickTake ? 'digest-quick-take-card' : ''}`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left group"
      >
        <div className="flex items-center gap-2">
          {section.emoji && <span className="text-lg">{section.emoji}</span>}
          <h3 className="font-semibold text-sm tracking-wide text-apple-gray-800">
            {section.title}
          </h3>
        </div>
        <span className="text-apple-gray-400 group-hover:text-apple-gray-600 transition-colors">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </span>
      </button>

      {/* Body */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-apple-gray-100">
          {/* Data content */}
          {quickTake ? (
            <QuickTakeContent html={section.dataHtml + (section.analysisHtml ? '\n' + section.analysisHtml : '')} />
          ) : (
            <>
              {section.dataHtml && (
                <div
                  className="digest-data"
                  dangerouslySetInnerHTML={{ __html: section.dataHtml }}
                />
              )}

              {/* Analysis aside */}
              {section.analysisHtml && (
                <div className="digest-analysis mt-3">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-blue-500 mb-1">
                    Analysis
                  </div>
                  <div
                    className="text-sm text-apple-gray-600 leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: section.analysisHtml }}
                  />
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
