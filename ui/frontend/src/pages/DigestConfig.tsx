import { useState, useEffect } from 'react'
import { Save, ChevronUp, ChevronDown, GripVertical } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import api from '../api/client'
import type { DigestConfig } from '../api/types'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ToastContainer from '../components/common/Toast'

const DIGEST_TYPES = ['morning', 'afternoon', 'weekly'] as const
const MODE_OPTIONS = ['facts', 'full', 'both']

const SECTION_LABELS: Record<string, string> = {
  overnight: 'Overnight Recap',
  futures: 'US Futures',
  forex: 'Forex Majors',
  commodities: 'Commodities',
  crypto: 'Crypto',
  calendar: 'Economic Calendar',
  sentiment: 'Market Sentiment',
  indices_close: 'Indices Closing',
  sentiment_shift: 'Sentiment Shift',
  movers: 'Key Movers',
  week_review: 'Week in Review',
  rankings: 'Performance Rankings',
  sectors: 'Sector Comparison',
  economic: 'Economic Data',
  technicals: 'Technical Outlook',
  next_steps: 'Next Steps',
}

export default function DigestConfig() {
  const { data: config, loading, refetch } = useApi<Record<string, DigestConfig>>('/digests/config')
  const { toasts, addToast, removeToast } = useToast()
  const [activeTab, setActiveTab] = useState<typeof DIGEST_TYPES[number]>('morning')
  const [editing, setEditing] = useState<Record<string, DigestConfig>>({})

  useEffect(() => {
    if (config) setEditing(JSON.parse(JSON.stringify(config)))
  }, [config])

  const current = editing[activeTab]

  const moveSection = (index: number, direction: 'up' | 'down') => {
    if (!current) return
    const sections = [...current.sections]
    const swapIndex = direction === 'up' ? index - 1 : index + 1
    if (swapIndex < 0 || swapIndex >= sections.length) return
    ;[sections[index], sections[swapIndex]] = [sections[swapIndex], sections[index]]
    setEditing(prev => ({
      ...prev,
      [activeTab]: { ...prev[activeTab], sections },
    }))
  }

  const removeSection = (index: number) => {
    if (!current) return
    const sections = current.sections.filter((_, i) => i !== index)
    setEditing(prev => ({
      ...prev,
      [activeTab]: { ...prev[activeTab], sections },
    }))
  }

  const save = async () => {
    try {
      await api.put(`/digests/config/${activeTab}`, editing[activeTab])
      addToast(`${activeTab} config saved`, 'success')
      refetch()
    } catch {
      addToast('Failed to save', 'error')
    }
  }

  if (loading || !current) return <LoadingSpinner size="lg" className="mt-20" />

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold mb-1">Digest Configuration</h1>
      <p className="text-apple-gray-400 text-sm mb-8">Configure sections, order, mode, and schedule for each digest type</p>

      {/* Tabs */}
      <div className="flex gap-1 mb-6">
        {DIGEST_TYPES.map(type => (
          <button
            key={type}
            onClick={() => setActiveTab(type)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
              activeTab === type ? 'bg-apple-blue text-white' : 'bg-white text-apple-gray-500 hover:bg-apple-gray-200'
            }`}
          >
            {type}
          </button>
        ))}
      </div>

      <div className="card mb-6">
        {/* Default Mode */}
        <div className="mb-6">
          <label className="label">Default Mode</label>
          <div className="flex flex-wrap gap-2">
            {MODE_OPTIONS.map(mode => (
              <button
                key={mode}
                onClick={() => setEditing(prev => ({
                  ...prev,
                  [activeTab]: { ...prev[activeTab], default_mode: mode },
                }))}
                className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                  current.default_mode === mode ? 'bg-apple-blue text-white' : 'bg-apple-gray-100 text-apple-gray-500 hover:bg-apple-gray-200'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        {/* Schedule */}
        <div className="mb-6">
          <label className="label">Schedule</label>
          <input
            className="input-field !w-48"
            value={current.schedule}
            onChange={e => setEditing(prev => ({
              ...prev,
              [activeTab]: { ...prev[activeTab], schedule: e.target.value },
            }))}
            placeholder="e.g. 06:30"
          />
          <p className="text-xs text-apple-gray-400 mt-1">
            {activeTab === 'weekly' ? 'Format: "fri 17:30"' : 'Format: "HH:MM" in your timezone'}
          </p>
        </div>

        {/* Section Order */}
        <div>
          <label className="label">Section Order</label>
          <div className="space-y-1">
            {current.sections.map((section, i) => (
              <div key={`${section}-${i}`} className="flex items-center gap-3 p-3 bg-apple-gray-50 rounded-lg">
                <GripVertical size={14} className="text-apple-gray-300" />
                <span className="text-sm font-medium flex-1">{SECTION_LABELS[section] || section}</span>
                <div className="flex gap-1">
                  <button onClick={() => moveSection(i, 'up')} disabled={i === 0} className="p-1 text-apple-gray-400 hover:text-apple-gray-600 disabled:opacity-30">
                    <ChevronUp size={14} />
                  </button>
                  <button onClick={() => moveSection(i, 'down')} disabled={i === current.sections.length - 1} className="p-1 text-apple-gray-400 hover:text-apple-gray-600 disabled:opacity-30">
                    <ChevronDown size={14} />
                  </button>
                  <button onClick={() => removeSection(i)} className="p-1 text-apple-gray-300 hover:text-apple-red">
                    &times;
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button onClick={save} className="btn-primary flex items-center gap-2">
          <Save size={14} /> Save Configuration
        </button>
      </div>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
