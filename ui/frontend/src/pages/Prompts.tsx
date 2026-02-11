import { useState, useEffect } from 'react'
import { RotateCcw, ChevronDown, ChevronUp, GripVertical, Save } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import api from '../api/client'
import type { PromptsConfig, LLMConfig } from '../api/types'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ToastContainer from '../components/common/Toast'

const SECTION_LABELS: Record<string, string> = {
  overnight: 'Overnight Recap',
  futures: 'US Futures Pre-Market',
  forex: 'Forex Majors',
  commodities: 'Commodities',
  crypto: 'Cryptocurrency',
  calendar: 'Economic Calendar',
  sentiment: 'Market Sentiment',
  indices_close: 'US Indices Closing',
  sentiment_shift: 'Sentiment Shift',
  movers: 'Key Movers',
  week_review: 'Week in Review',
  rankings: 'Performance Rankings',
  sectors: 'Sector Comparison',
  economic: 'Economic Data Recap',
  technicals: 'Technical Outlook',
  next_steps_morning: 'Next Steps (Morning)',
  next_steps_afternoon: 'Next Steps (Afternoon)',
  next_steps_weekly: 'Next Steps (Weekly)',
}

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Anthropic (Claude)',
  openai: 'OpenAI',
  gemini: 'Google Gemini',
}

export default function Prompts() {
  const { data: config, loading, refetch } = useApi<PromptsConfig>('/prompts')
  const { data: llmConfig, refetch: refetchLlm } = useApi<LLMConfig>('/prompts/llm-config')
  const { toasts, addToast, removeToast } = useToast()
  const [systemPrompt, setSystemPrompt] = useState('')
  const [expandedSection, setExpandedSection] = useState<string | null>(null)
  const [editingPrompts, setEditingPrompts] = useState<Record<string, { prompt: string; max_tokens: number; include_cross_context: boolean }>>({})
  const [providerPriority, setProviderPriority] = useState<string[]>([])
  const [providerModels, setProviderModels] = useState<Record<string, string>>({})

  useEffect(() => {
    if (config) setSystemPrompt(config.system_prompt)
  }, [config])

  useEffect(() => {
    if (llmConfig) {
      setProviderPriority(llmConfig.provider_priority)
      setProviderModels(llmConfig.provider_models)
    }
  }, [llmConfig])

  const saveSystemPrompt = async () => {
    try {
      await api.put('/prompts/system', { system_prompt: systemPrompt })
      addToast('System prompt saved', 'success')
    } catch {
      addToast('Failed to save', 'error')
    }
  }

  const saveSectionPrompt = async (section: string) => {
    const edit = editingPrompts[section]
    if (!edit) return
    try {
      await api.put(`/prompts/sections/${section}`, edit)
      addToast(`${SECTION_LABELS[section]} saved`, 'success')
      refetch()
    } catch {
      addToast('Failed to save', 'error')
    }
  }

  const resetSection = async (section: string) => {
    try {
      const res = await api.post(`/prompts/reset/${section}`)
      setEditingPrompts(prev => {
        const copy = { ...prev }
        delete copy[section]
        return copy
      })
      addToast(`${SECTION_LABELS[section]} reset to default`, 'success')
      refetch()
    } catch {
      addToast('Failed to reset', 'error')
    }
  }

  const resetAll = async () => {
    try {
      await api.post('/prompts/reset-all')
      setEditingPrompts({})
      addToast('All prompts reset to defaults', 'success')
      refetch()
    } catch {
      addToast('Failed to reset', 'error')
    }
  }

  const saveLlmConfig = async () => {
    try {
      await api.put('/prompts/llm-config', { provider_priority: providerPriority, provider_models: providerModels })
      addToast('LLM config saved', 'success')
    } catch {
      addToast('Failed to save', 'error')
    }
  }

  const moveProvider = (index: number, direction: 'up' | 'down') => {
    const newPriority = [...providerPriority]
    const swapIndex = direction === 'up' ? index - 1 : index + 1
    if (swapIndex < 0 || swapIndex >= newPriority.length) return
    ;[newPriority[index], newPriority[swapIndex]] = [newPriority[swapIndex], newPriority[index]]
    setProviderPriority(newPriority)
  }

  const openSection = (section: string) => {
    if (expandedSection === section) {
      setExpandedSection(null)
      return
    }
    setExpandedSection(section)
    if (!editingPrompts[section] && config) {
      const sectionConfig = config.sections[section]
      setEditingPrompts(prev => ({
        ...prev,
        [section]: {
          prompt: sectionConfig.prompt,
          max_tokens: sectionConfig.max_tokens,
          include_cross_context: sectionConfig.include_cross_context,
        },
      }))
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />
  if (!config) return null

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold mb-1">Prompts</h1>
      <p className="text-apple-gray-400 text-sm mb-8">Configure LLM system prompt, section prompts, and provider priority</p>

      {/* System Prompt */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium">System Prompt</h3>
          <span className="text-xs text-apple-gray-400">{systemPrompt.length} chars</span>
        </div>
        <textarea
          className="textarea-field min-h-[200px]"
          value={systemPrompt}
          onChange={e => setSystemPrompt(e.target.value)}
        />
        <div className="flex justify-end gap-3 mt-3">
          <button onClick={() => setSystemPrompt(config.system_prompt)} className="btn-secondary text-xs">Reset</button>
          <button onClick={saveSystemPrompt} className="btn-primary text-xs flex items-center gap-1">
            <Save size={12} /> Save
          </button>
        </div>
      </div>

      {/* LLM Provider Config */}
      <div className="card mb-6">
        <h3 className="font-medium mb-4">LLM Provider Priority</h3>
        <p className="text-xs text-apple-gray-400 mb-3">
          Providers are tried in order. First available provider is used.
        </p>
        <div className="space-y-2 mb-4">
          {providerPriority.map((provider, i) => (
            <div key={provider} className="flex flex-wrap items-center gap-3 p-3 bg-apple-gray-50 rounded-lg">
              <GripVertical size={14} className="text-apple-gray-300" />
              <span className="text-sm font-medium flex-1">{PROVIDER_LABELS[provider] || provider}</span>
              <input
                className="input-field w-full sm:!w-48 text-xs"
                value={providerModels[provider] || ''}
                onChange={e => setProviderModels(prev => ({ ...prev, [provider]: e.target.value }))}
                placeholder="Model name"
              />
              <div className="flex gap-1">
                <button onClick={() => moveProvider(i, 'up')} disabled={i === 0} className="p-1 text-apple-gray-400 hover:text-apple-gray-600 disabled:opacity-30">
                  <ChevronUp size={14} />
                </button>
                <button onClick={() => moveProvider(i, 'down')} disabled={i === providerPriority.length - 1} className="p-1 text-apple-gray-400 hover:text-apple-gray-600 disabled:opacity-30">
                  <ChevronDown size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
        <button onClick={saveLlmConfig} className="btn-primary text-xs flex items-center gap-1">
          <Save size={12} /> Save Provider Config
        </button>
      </div>

      {/* Section Prompts */}
      <div className="card mb-6">
        <h3 className="font-medium mb-4">Section Prompts</h3>
        <div className="space-y-1">
          {config.section_names.map(section => {
            const sectionConfig = config.sections[section]
            const isExpanded = expandedSection === section
            const edit = editingPrompts[section]

            return (
              <div key={section} className="border border-apple-gray-100 rounded-lg overflow-hidden">
                <button
                  onClick={() => openSection(section)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-apple-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium">{SECTION_LABELS[section] || section}</span>
                    {sectionConfig.is_default && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-apple-gray-100 text-apple-gray-400">default</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-apple-gray-400">
                    <span className="text-xs">{sectionConfig.max_tokens} tokens</span>
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </div>
                </button>
                {isExpanded && edit && (
                  <div className="px-4 pb-4 space-y-3 border-t border-apple-gray-100 pt-3">
                    <textarea
                      className="textarea-field min-h-[120px]"
                      value={edit.prompt}
                      onChange={e => setEditingPrompts(prev => ({
                        ...prev,
                        [section]: { ...prev[section], prompt: e.target.value },
                      }))}
                    />
                    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-6">
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-apple-gray-500">Max Tokens:</label>
                        <input
                          type="range"
                          min={100}
                          max={1000}
                          step={50}
                          value={edit.max_tokens}
                          onChange={e => setEditingPrompts(prev => ({
                            ...prev,
                            [section]: { ...prev[section], max_tokens: parseInt(e.target.value) },
                          }))}
                          className="w-32"
                        />
                        <span className="text-xs font-mono text-apple-gray-500 w-10">{edit.max_tokens}</span>
                      </div>
                      <label className="flex items-center gap-2 text-xs text-apple-gray-500">
                        <input
                          type="checkbox"
                          checked={edit.include_cross_context}
                          onChange={e => setEditingPrompts(prev => ({
                            ...prev,
                            [section]: { ...prev[section], include_cross_context: e.target.checked },
                          }))}
                          className="rounded"
                        />
                        Include cross-context
                      </label>
                    </div>
                    <div className="flex justify-end gap-2">
                      <button onClick={() => resetSection(section)} className="btn-secondary text-xs flex items-center gap-1">
                        <RotateCcw size={12} /> Reset Default
                      </button>
                      <button onClick={() => saveSectionPrompt(section)} className="btn-primary text-xs flex items-center gap-1">
                        <Save size={12} /> Save
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Reset All */}
      <div className="flex justify-end">
        <button onClick={resetAll} className="btn-danger text-xs flex items-center gap-1">
          <RotateCcw size={12} /> Reset All Prompts to Defaults
        </button>
      </div>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
