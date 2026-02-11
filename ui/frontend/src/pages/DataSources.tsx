import { useState, useEffect } from 'react'
import { Loader2, Wifi, WifiOff, Plus, Trash2, Pencil, ToggleLeft, ToggleRight, Zap, X } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import api from '../api/client'
import type { DataSource, CacheStats, TestResult, CustomSource } from '../api/types'
import StatusDot from '../components/common/StatusDot'
import MaskedField from '../components/common/MaskedField'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ToastContainer from '../components/common/Toast'

const SOURCE_TYPES = ['http', 'rss', 'csv'] as const
const AUTH_TYPES = ['none', 'api_key', 'bearer', 'header'] as const
const DIGEST_TYPES = ['morning', 'afternoon', 'weekly', 'daytrade'] as const
const INTEGRATION_MODES = ['section', 'merge'] as const

type SourceType = typeof SOURCE_TYPES[number]

interface FormState {
  name: string
  type: SourceType
  enabled: boolean
  url: string
  path: string
  auth_type: string
  auth_env_var: string
  auth_header_name: string
  response_root: string
  response_mapping: string // JSON string
  instruments: string // comma-separated
  field_mapping: string // JSON string
  columns: string // JSON string
  max_items: number
  cache_ttl: number
  integration_mode: string
  merge_target: string
  section_title: string
  digest_types: string[]
}

const emptyForm: FormState = {
  name: '',
  type: 'http',
  enabled: true,
  url: '',
  path: '',
  auth_type: 'none',
  auth_env_var: '',
  auth_header_name: '',
  response_root: '',
  response_mapping: '',
  instruments: '',
  field_mapping: '',
  columns: '',
  max_items: 10,
  cache_ttl: 300,
  integration_mode: 'section',
  merge_target: '',
  section_title: '',
  digest_types: ['morning'],
}

function sourceToForm(source: CustomSource): FormState {
  return {
    name: source.name,
    type: source.type as SourceType,
    enabled: source.enabled,
    url: source.url || '',
    path: source.path || '',
    auth_type: source.auth?.type || 'none',
    auth_env_var: source.auth?.env_var || '',
    auth_header_name: source.auth?.header_name || '',
    response_root: source.response_root || '',
    response_mapping: source.response_mapping ? JSON.stringify(source.response_mapping) : '',
    instruments: source.instruments?.join(', ') || '',
    field_mapping: source.field_mapping ? JSON.stringify(source.field_mapping) : '',
    columns: source.columns ? JSON.stringify(source.columns) : '',
    max_items: source.max_items || 10,
    cache_ttl: source.cache_ttl,
    integration_mode: source.digest_integration?.mode || 'section',
    merge_target: source.digest_integration?.merge_target || '',
    section_title: source.digest_integration?.section_title || '',
    digest_types: source.digest_integration?.digest_types || ['morning'],
  }
}

function formToPayload(form: FormState) {
  const payload: any = {
    name: form.name,
    type: form.type,
    enabled: form.enabled,
    cache_ttl: form.cache_ttl,
    digest_integration: {
      mode: form.integration_mode,
      section_title: form.section_title || form.name,
      digest_types: form.digest_types,
      ...(form.integration_mode === 'merge' && form.merge_target ? { merge_target: form.merge_target } : {}),
    },
  }

  if (form.type === 'http' || form.type === 'rss') {
    payload.url = form.url
  }
  if (form.type === 'csv') {
    payload.path = form.path
  }
  if (form.type === 'http' && form.auth_type !== 'none') {
    payload.auth = {
      type: form.auth_type,
      ...(form.auth_env_var ? { env_var: form.auth_env_var } : {}),
      ...(form.auth_header_name ? { header_name: form.auth_header_name } : {}),
    }
  }
  if (form.type === 'http') {
    if (form.response_root) payload.response_root = form.response_root
    if (form.response_mapping) {
      try { payload.response_mapping = JSON.parse(form.response_mapping) } catch {}
    }
    if (form.instruments) {
      payload.instruments = form.instruments.split(',').map(s => s.trim()).filter(Boolean)
    }
  }
  if (form.type === 'rss') {
    payload.max_items = form.max_items
    if (form.field_mapping) {
      try { payload.field_mapping = JSON.parse(form.field_mapping) } catch {}
    }
  }
  if (form.type === 'csv') {
    if (form.columns) {
      try { payload.columns = JSON.parse(form.columns) } catch {}
    }
  }

  return payload
}

export default function DataSources() {
  const { data: sources, loading, refetch } = useApi<DataSource[]>('/sources')
  const { data: cacheStats, refetch: refetchCache } = useApi<CacheStats>('/cache/stats')
  const { toasts, addToast, removeToast } = useToast()
  const [testing, setTesting] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({})
  const [editingKey, setEditingKey] = useState<Record<string, string>>({})

  // Custom sources state
  const [customSources, setCustomSources] = useState<CustomSource[]>([])
  const [customLoading, setCustomLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingSourceId, setEditingSourceId] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [step, setStep] = useState(1)

  const fetchCustomSources = async () => {
    try {
      const res = await api.get('/sources/custom')
      setCustomSources(res.data)
    } catch {
      // no custom sources yet — OK
    } finally {
      setCustomLoading(false)
    }
  }

  useEffect(() => { fetchCustomSources() }, [])

  const testSource = async (id: string) => {
    setTesting(id)
    try {
      const res = await api.post(`/sources/${id}/test`)
      setTestResults(prev => ({ ...prev, [id]: res.data }))
      addToast(res.data.success ? `${id}: ${res.data.message}` : `${id} failed: ${res.data.message}`, res.data.success ? 'success' : 'error')
    } catch (err: any) {
      setTestResults(prev => ({ ...prev, [id]: { success: false, message: 'Test failed' } }))
    } finally {
      setTesting(null)
    }
  }

  const testCustomSource = async (id: string) => {
    setTesting(id)
    try {
      const res = await api.post(`/sources/custom/${id}/test`)
      setTestResults(prev => ({ ...prev, [id]: res.data }))
      addToast(res.data.success ? `${id}: ${res.data.message}` : `${id} failed: ${res.data.message}`, res.data.success ? 'success' : 'error')
    } catch {
      setTestResults(prev => ({ ...prev, [id]: { success: false, message: 'Test failed' } }))
    } finally {
      setTesting(null)
    }
  }

  const toggleCustomSource = async (id: string, enabled: boolean) => {
    try {
      await api.put(`/sources/custom/${id}/toggle`, { enabled })
      addToast(`Source ${enabled ? 'enabled' : 'disabled'}`, 'success')
      fetchCustomSources()
    } catch {
      addToast('Toggle failed', 'error')
    }
  }

  const deleteCustomSource = async (id: string) => {
    try {
      await api.delete(`/sources/custom/${id}`)
      addToast('Source deleted', 'success')
      fetchCustomSources()
    } catch {
      addToast('Delete failed', 'error')
    }
  }

  const saveApiKey = async (id: string) => {
    try {
      await api.put(`/sources/${id}/api-key`, { key: id, value: editingKey[id] || '' })
      addToast('API key saved', 'success')
      refetch()
    } catch (err: any) {
      addToast('Failed to save key', 'error')
    }
  }

  const clearCache = async () => {
    try {
      const res = await api.post('/cache/clear')
      addToast(`Cleared ${res.data.removed} cache files`, 'success')
      refetchCache()
    } catch {
      addToast('Failed to clear cache', 'error')
    }
  }

  const clearExpired = async () => {
    try {
      const res = await api.post('/cache/clear-expired')
      addToast(`Removed ${res.data.removed} expired files`, 'success')
      refetchCache()
    } catch {
      addToast('Failed to clear expired cache', 'error')
    }
  }

  const openAddModal = () => {
    setForm(emptyForm)
    setEditingSourceId(null)
    setStep(1)
    setShowModal(true)
  }

  const openEditModal = (source: CustomSource) => {
    setForm(sourceToForm(source))
    setEditingSourceId(source.id)
    setStep(1)
    setShowModal(true)
  }

  const saveCustomSource = async () => {
    try {
      const payload = formToPayload(form)
      if (editingSourceId) {
        await api.put(`/sources/custom/${editingSourceId}`, payload)
        addToast('Source updated', 'success')
      } else {
        await api.post('/sources/custom', payload)
        addToast('Source created', 'success')
      }
      setShowModal(false)
      fetchCustomSources()
    } catch (err: any) {
      addToast(err?.response?.data?.detail || 'Save failed', 'error')
    }
  }

  const updateForm = (updates: Partial<FormState>) => setForm(prev => ({ ...prev, ...updates }))

  const typeBadge = (t: string) => {
    const colors: Record<string, string> = {
      http: 'bg-blue-100 text-blue-700',
      rss: 'bg-orange-100 text-orange-700',
      csv: 'bg-green-100 text-green-700',
    }
    return <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase ${colors[t] || 'bg-gray-100 text-gray-600'}`}>{t}</span>
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold mb-1">Data Sources</h1>
      <p className="text-apple-gray-400 text-sm mb-8">Manage API connections, custom sources, and cache</p>

      {/* Built-in Sources */}
      <h2 className="text-lg font-medium mb-4">Built-in Sources</h2>
      <div className="space-y-4 mb-8">
        {sources?.map(source => (
          <div key={source.id} className="card">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${source.configured ? 'bg-apple-green/10' : 'bg-apple-gray-100'}`}>
                  {source.configured ? <Wifi size={18} className="text-apple-green" /> : <WifiOff size={18} className="text-apple-gray-400" />}
                </div>
                <div>
                  <h3 className="font-medium">{source.name}</h3>
                  <p className="text-xs text-apple-gray-400">{source.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusDot status={source.configured ? 'green' : 'gray'} size="md" />
                <span className="text-xs text-apple-gray-400">
                  {source.configured ? 'Connected' : 'Not configured'}
                </span>
              </div>
            </div>

            <div className="mt-4 flex items-center gap-3">
              {source.needs_key && (
                <div className="flex-1">
                  <MaskedField
                    value={editingKey[source.id] || ''}
                    onChange={v => setEditingKey(prev => ({ ...prev, [source.id]: v }))}
                    placeholder="Enter API key"
                    onSave={() => saveApiKey(source.id)}
                  />
                </div>
              )}
              <button
                onClick={() => testSource(source.id)}
                disabled={testing === source.id}
                className="btn-secondary flex items-center gap-2 whitespace-nowrap"
              >
                {testing === source.id ? <Loader2 size={14} className="animate-spin" /> : null}
                Test
              </button>
            </div>

            {testResults[source.id] && (
              <div className={`mt-3 text-xs px-3 py-2 rounded-lg ${testResults[source.id].success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                {testResults[source.id].message}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Custom Sources */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium">Custom Sources</h2>
        <button onClick={openAddModal} className="btn-primary flex items-center gap-2 text-sm">
          <Plus size={14} /> Add Custom Source
        </button>
      </div>

      {customLoading ? (
        <LoadingSpinner size="sm" className="mb-8" />
      ) : customSources.length === 0 ? (
        <div className="card text-center text-apple-gray-400 text-sm py-8 mb-8">
          No custom sources configured yet. Add an HTTP API, RSS feed, or CSV file.
        </div>
      ) : (
        <div className="space-y-4 mb-8">
          {customSources.map(src => (
            <div key={src.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{src.name}</h3>
                      {typeBadge(src.type)}
                    </div>
                    <p className="text-xs text-apple-gray-400 mt-0.5">
                      {src.url || src.path || 'No URL'}
                      {src.digest_integration?.digest_types?.length ? ` — ${src.digest_integration.digest_types.join(', ')}` : ''}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleCustomSource(src.id, !src.enabled)}
                    className="text-apple-gray-400 hover:text-apple-gray-600"
                    title={src.enabled ? 'Disable' : 'Enable'}
                  >
                    {src.enabled ? <ToggleRight size={20} className="text-apple-green" /> : <ToggleLeft size={20} />}
                  </button>
                  <button
                    onClick={() => testCustomSource(src.id)}
                    disabled={testing === src.id}
                    className="btn-secondary text-xs px-2 py-1 flex items-center gap-1"
                  >
                    {testing === src.id ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
                    Test
                  </button>
                  <button onClick={() => openEditModal(src)} className="text-apple-gray-400 hover:text-apple-blue" title="Edit">
                    <Pencil size={14} />
                  </button>
                  <button onClick={() => deleteCustomSource(src.id)} className="text-apple-gray-400 hover:text-red-500" title="Delete">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
              {testResults[src.id] && (
                <div className={`mt-3 text-xs px-3 py-2 rounded-lg ${testResults[src.id].success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                  {testResults[src.id].message}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Cache Controls */}
      <div className="card">
        <h3 className="font-medium mb-4">Cache Management</h3>
        <div className="flex items-center gap-6 mb-4 text-sm">
          <div>
            <span className="text-apple-gray-400">Files:</span>{' '}
            <span className="font-medium">{cacheStats?.file_count ?? 0}</span>
          </div>
          <div>
            <span className="text-apple-gray-400">Size:</span>{' '}
            <span className="font-medium">{((cacheStats?.total_size_bytes ?? 0) / 1024).toFixed(1)} KB</span>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <button onClick={clearExpired} className="btn-secondary">Clear Expired</button>
          <button onClick={clearCache} className="btn-danger">Clear All Cache</button>
        </div>
      </div>

      {/* Add/Edit Custom Source Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b">
              <h2 className="text-lg font-semibold">{editingSourceId ? 'Edit' : 'Add'} Custom Source</h2>
              <button onClick={() => setShowModal(false)} className="text-apple-gray-400 hover:text-apple-gray-600">
                <X size={18} />
              </button>
            </div>

            <div className="p-5 space-y-5">
              {/* Step indicators */}
              <div className="flex gap-2 mb-2">
                {[1, 2, 3, 4].map(s => (
                  <button
                    key={s}
                    onClick={() => setStep(s)}
                    className={`flex-1 h-1.5 rounded-full transition-colors ${step >= s ? 'bg-apple-blue' : 'bg-apple-gray-100'}`}
                  />
                ))}
              </div>
              <p className="text-xs text-apple-gray-400">
                Step {step} of 4: {['Basics', 'Connection', 'Field Mapping', 'Digest Integration'][step - 1]}
              </p>

              {/* Step 1: Basics */}
              {step === 1 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Name</label>
                    <input
                      value={form.name}
                      onChange={e => updateForm({ name: e.target.value })}
                      className="input w-full"
                      placeholder="My Data Source"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Type</label>
                    <div className="flex gap-2">
                      {SOURCE_TYPES.map(t => (
                        <button
                          key={t}
                          onClick={() => updateForm({ type: t })}
                          className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${form.type === t ? 'border-apple-blue bg-apple-blue/5 text-apple-blue' : 'border-apple-gray-200 text-apple-gray-500 hover:border-apple-gray-300'}`}
                        >
                          {t.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={form.enabled}
                      onChange={e => updateForm({ enabled: e.target.checked })}
                      className="rounded"
                    />
                    Enabled
                  </label>
                </div>
              )}

              {/* Step 2: Connection */}
              {step === 2 && (
                <div className="space-y-4">
                  {(form.type === 'http' || form.type === 'rss') && (
                    <div>
                      <label className="block text-sm font-medium mb-1">URL</label>
                      <input
                        value={form.url}
                        onChange={e => updateForm({ url: e.target.value })}
                        className="input w-full"
                        placeholder="https://api.example.com/data?symbol={symbol}&key={api_key}"
                      />
                      {form.type === 'http' && (
                        <p className="text-xs text-apple-gray-400 mt-1">Use {'{symbol}'} and {'{api_key}'} as placeholders</p>
                      )}
                    </div>
                  )}
                  {form.type === 'csv' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">File Path (relative to project root)</label>
                      <input
                        value={form.path}
                        onChange={e => updateForm({ path: e.target.value })}
                        className="input w-full"
                        placeholder="data/watchlist.csv"
                      />
                    </div>
                  )}
                  {form.type === 'http' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium mb-1">Authentication</label>
                        <select
                          value={form.auth_type}
                          onChange={e => updateForm({ auth_type: e.target.value })}
                          className="input w-full"
                        >
                          {AUTH_TYPES.map(a => (
                            <option key={a} value={a}>{a === 'none' ? 'None' : a === 'api_key' ? 'API Key in URL' : a === 'bearer' ? 'Bearer Token' : 'Custom Header'}</option>
                          ))}
                        </select>
                      </div>
                      {form.auth_type !== 'none' && (
                        <div>
                          <label className="block text-sm font-medium mb-1">Environment Variable</label>
                          <input
                            value={form.auth_env_var}
                            onChange={e => updateForm({ auth_env_var: e.target.value })}
                            className="input w-full"
                            placeholder="ALPHAVANTAGE_KEY"
                          />
                        </div>
                      )}
                      {form.auth_type === 'header' && (
                        <div>
                          <label className="block text-sm font-medium mb-1">Header Name</label>
                          <input
                            value={form.auth_header_name}
                            onChange={e => updateForm({ auth_header_name: e.target.value })}
                            className="input w-full"
                            placeholder="X-API-Key"
                          />
                        </div>
                      )}
                      <div>
                        <label className="block text-sm font-medium mb-1">Instruments (comma-separated)</label>
                        <input
                          value={form.instruments}
                          onChange={e => updateForm({ instruments: e.target.value })}
                          className="input w-full"
                          placeholder="AAPL, MSFT, GOLD"
                        />
                      </div>
                    </>
                  )}
                  {form.type === 'rss' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">Max Items</label>
                      <input
                        type="number"
                        value={form.max_items}
                        onChange={e => updateForm({ max_items: parseInt(e.target.value) || 10 })}
                        className="input w-24"
                      />
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-medium mb-1">Cache TTL (seconds)</label>
                    <input
                      type="number"
                      value={form.cache_ttl}
                      onChange={e => updateForm({ cache_ttl: parseInt(e.target.value) || 300 })}
                      className="input w-32"
                    />
                  </div>
                </div>
              )}

              {/* Step 3: Field Mapping */}
              {step === 3 && (
                <div className="space-y-4">
                  {form.type === 'http' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium mb-1">Response Root (dot-notation path)</label>
                        <input
                          value={form.response_root}
                          onChange={e => updateForm({ response_root: e.target.value })}
                          className="input w-full"
                          placeholder='e.g. "Global Quote" or "data.results"'
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">Response Mapping (JSON)</label>
                        <textarea
                          value={form.response_mapping}
                          onChange={e => updateForm({ response_mapping: e.target.value })}
                          className="input w-full h-24 font-mono text-xs"
                          placeholder='{"price": "05. price", "change_pct": "10. change percent"}'
                        />
                        <p className="text-xs text-apple-gray-400 mt-1">Maps your field names to the API's field names</p>
                      </div>
                    </>
                  )}
                  {form.type === 'rss' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">Field Mapping (JSON)</label>
                      <textarea
                        value={form.field_mapping}
                        onChange={e => updateForm({ field_mapping: e.target.value })}
                        className="input w-full h-24 font-mono text-xs"
                        placeholder='{"title": "title", "summary": "description", "url": "link"}'
                      />
                    </div>
                  )}
                  {form.type === 'csv' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">Column Mapping (JSON)</label>
                      <textarea
                        value={form.columns}
                        onChange={e => updateForm({ columns: e.target.value })}
                        className="input w-full h-24 font-mono text-xs"
                        placeholder='{"symbol": "Ticker", "price": "Last Price", "change_pct": "Change %"}'
                      />
                      <p className="text-xs text-apple-gray-400 mt-1">Maps your field names to CSV column headers</p>
                    </div>
                  )}
                  {(form.type === 'rss' || form.type === 'csv') && !form.field_mapping && !form.columns && (
                    <p className="text-sm text-apple-gray-400">Leave empty to use default field names.</p>
                  )}
                </div>
              )}

              {/* Step 4: Digest Integration */}
              {step === 4 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Integration Mode</label>
                    <div className="flex gap-2">
                      {INTEGRATION_MODES.map(m => (
                        <button
                          key={m}
                          onClick={() => updateForm({ integration_mode: m })}
                          className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${form.integration_mode === m ? 'border-apple-blue bg-apple-blue/5 text-apple-blue' : 'border-apple-gray-200 text-apple-gray-500 hover:border-apple-gray-300'}`}
                        >
                          {m === 'section' ? 'New Section' : 'Merge into Existing'}
                        </button>
                      ))}
                    </div>
                  </div>
                  {form.integration_mode === 'section' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">Section Title</label>
                      <input
                        value={form.section_title}
                        onChange={e => updateForm({ section_title: e.target.value })}
                        className="input w-full"
                        placeholder={form.name || 'Custom Data'}
                      />
                    </div>
                  )}
                  {form.integration_mode === 'merge' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">Merge Target Section</label>
                      <input
                        value={form.merge_target}
                        onChange={e => updateForm({ merge_target: e.target.value })}
                        className="input w-full"
                        placeholder="e.g. forex, commodities, crypto"
                      />
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-medium mb-2">Digest Types</label>
                    <div className="flex flex-wrap gap-2">
                      {DIGEST_TYPES.map(dt => (
                        <label key={dt} className="flex items-center gap-1.5 text-sm">
                          <input
                            type="checkbox"
                            checked={form.digest_types.includes(dt)}
                            onChange={e => {
                              const updated = e.target.checked
                                ? [...form.digest_types, dt]
                                : form.digest_types.filter(t => t !== dt)
                              updateForm({ digest_types: updated })
                            }}
                            className="rounded"
                          />
                          {dt}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Modal footer */}
            <div className="flex items-center justify-between p-5 border-t">
              <button
                onClick={() => step > 1 ? setStep(step - 1) : setShowModal(false)}
                className="btn-secondary text-sm"
              >
                {step > 1 ? 'Back' : 'Cancel'}
              </button>
              <div className="flex gap-2">
                {step < 4 ? (
                  <button
                    onClick={() => setStep(step + 1)}
                    disabled={step === 1 && !form.name}
                    className="btn-primary text-sm"
                  >
                    Next
                  </button>
                ) : (
                  <button
                    onClick={saveCustomSource}
                    disabled={!form.name}
                    className="btn-primary text-sm"
                  >
                    {editingSourceId ? 'Save Changes' : 'Create Source'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
