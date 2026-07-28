import { useState, useEffect } from 'react'
import api from '../api/client'
import type { PineStrategy } from '../api/signals-types'

export default function PineScripts() {
  const [strategies, setStrategies] = useState<PineStrategy[]>([])
  const [selected, setSelected] = useState('ema_crossover')
  const [script, setScript] = useState('')
  const [generating, setGenerating] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.get('/pine/strategies').then(res => {
      setStrategies(res.data.strategies || [])
    }).catch(() => {})
  }, [])

  const generate = async () => {
    setGenerating(true)
    try {
      const res = await api.post('/pine/generate', { strategy: selected })
      setScript(res.data.script || '')
    } catch { /* ignore */ }
    finally { setGenerating(false) }
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(script)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <h1 className="text-2xl font-bold mb-1">Pine Script Generator</h1>
      <p className="text-gray-500 text-sm mb-6">
        Generate TradingView Pine Scripts with 2:1 R/R targets built in
      </p>

      {/* Strategy Selection */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {strategies.map(s => (
          <button
            key={s.id}
            onClick={() => setSelected(s.id)}
            className={`text-left p-4 rounded-xl border transition-colors ${
              selected === s.id
                ? 'bg-blue-600/10 border-blue-500/50'
                : 'bg-gray-900 border-gray-800 hover:border-gray-700'
            }`}
          >
            <div className="font-medium">{s.name}</div>
            <div className="text-xs text-gray-500 mt-1">{s.description}</div>
          </button>
        ))}
      </div>

      <div className="flex gap-3 mb-6">
        <button
          onClick={generate}
          disabled={generating}
          className="px-6 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 disabled:opacity-50 transition-colors"
        >
          {generating ? 'Generating...' : 'Generate Pine Script'}
        </button>
        {script && (
          <button
            onClick={copyToClipboard}
            className="px-6 py-2.5 rounded-lg bg-gray-700 text-white font-medium hover:bg-gray-600 transition-colors"
          >
            {copied ? 'Copied!' : 'Copy to Clipboard'}
          </button>
        )}
      </div>

      {/* Script Preview */}
      {script && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 bg-gray-800">
            <span className="text-sm text-gray-400">Pine Script v5</span>
            <span className="text-xs text-gray-600">
              Paste into TradingView: Open Chart &gt; Pine Editor &gt; New Script
            </span>
          </div>
          <pre className="p-4 text-sm font-mono text-green-300 overflow-x-auto max-h-[600px] overflow-y-auto leading-relaxed">
            {script}
          </pre>
        </div>
      )}

      {/* Instructions */}
      <div className="mt-6 bg-gray-900 rounded-xl p-6 border border-gray-800">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">How to Use in TradingView</h3>
        <ol className="space-y-2 text-sm text-gray-500">
          <li><span className="text-gray-300 font-mono mr-2">1.</span>Click "Generate Pine Script" above</li>
          <li><span className="text-gray-300 font-mono mr-2">2.</span>Click "Copy to Clipboard"</li>
          <li><span className="text-gray-300 font-mono mr-2">3.</span>Open TradingView and go to your chart (USD/JPY, SPY, or AAPL)</li>
          <li><span className="text-gray-300 font-mono mr-2">4.</span>Click "Pine Editor" at the bottom of the chart</li>
          <li><span className="text-gray-300 font-mono mr-2">5.</span>Delete any existing code and paste the copied script</li>
          <li><span className="text-gray-300 font-mono mr-2">6.</span>Click "Add to Chart" to see signals on your chart</li>
          <li><span className="text-gray-300 font-mono mr-2">7.</span>The strategy tester tab will show historical performance</li>
        </ol>
        <div className="mt-4 text-xs text-gray-600 bg-gray-800 rounded p-3">
          All scripts include ATR-based stop losses and 2:1 minimum risk-reward targets.
          Parameters are adjustable via the script's Settings panel in TradingView.
        </div>
      </div>
    </div>
  )
}
