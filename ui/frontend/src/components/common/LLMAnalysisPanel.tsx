import { useState } from 'react'
import { Sparkles, ChevronDown, ChevronUp } from 'lucide-react'

interface LLMAnalysisPanelProps {
  analysis: string | null
  defaultOpen?: boolean
}

export default function LLMAnalysisPanel({ analysis, defaultOpen = false }: LLMAnalysisPanelProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="mt-3 rounded-xl bg-indigo-50 border border-indigo-100 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-left"
      >
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-indigo-500" />
          <span className="text-xs font-semibold text-indigo-700">AI Analysis</span>
        </div>
        {open ? (
          <ChevronUp size={14} className="text-indigo-400" />
        ) : (
          <ChevronDown size={14} className="text-indigo-400" />
        )}
      </button>
      {open && (
        <div className="px-4 pb-3">
          {analysis ? (
            <p className="text-xs text-indigo-900/80 leading-relaxed">{analysis}</p>
          ) : (
            <p className="text-xs text-indigo-400 italic">Enable LLM for AI analysis</p>
          )}
        </div>
      )}
    </div>
  )
}
