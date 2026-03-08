import { useState, useEffect } from 'react'
import { Save, Download, Upload, Plus, Trash2, Send, ChevronDown, ChevronUp, Check, X, Loader2, Key, Shield, Eye } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import api from '../api/client'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ToastContainer from '../components/common/Toast'
import MaskedField from '../components/common/MaskedField'

const TIMEZONES = [
  'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
  'UTC', 'Europe/London', 'Europe/Paris', 'Europe/Berlin',
  'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Singapore', 'Asia/Dubai',
  'Australia/Sydney',
]

const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR']

interface Recipient {
  chat_id: string
  label: string
}

interface ApiKeyStatus {
  key: string
  env_var: string
  label: string
  category: string
  configured: boolean
  masked_value: string
}

const CATEGORY_LABELS: Record<string, { label: string; description: string; icon: React.ReactNode }> = {
  telegram: { label: 'Telegram', description: 'Required for digest delivery', icon: <Send size={16} /> },
  data: { label: 'Data Sources', description: 'Market data providers (optional)', icon: <Eye size={16} /> },
  llm: { label: 'LLM Providers', description: 'AI analysis (optional, pick any one)', icon: <Shield size={16} /> },
  options: { label: 'Options Intelligence', description: 'Premium options data (optional)', icon: <Key size={16} /> },
}

const CATEGORY_ORDER = ['telegram', 'data', 'llm', 'options']

export default function Settings() {
  const { data: settings, loading } = useApi<{ timezone: string; log_level: string }>('/settings')
  const { toasts, addToast, removeToast } = useToast()
  const [timezone, setTimezone] = useState('US/Central')
  const [logLevel, setLogLevel] = useState('INFO')

  // Recipients state
  const [recipients, setRecipients] = useState<Recipient[]>([])
  const [loadingRecipients, setLoadingRecipients] = useState(true)
  const [newChatId, setNewChatId] = useState('')
  const [newLabel, setNewLabel] = useState('')
  const [testingId, setTestingId] = useState<string | null>(null)
  const [showGuide, setShowGuide] = useState(false)

  // API Keys state
  const [apiKeys, setApiKeys] = useState<ApiKeyStatus[]>([])
  const [loadingKeys, setLoadingKeys] = useState(true)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [keyValue, setKeyValue] = useState('')
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [testingApi, setTestingApi] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({})

  useEffect(() => {
    if (settings) {
      setTimezone(settings.timezone)
      setLogLevel(settings.log_level)
    }
  }, [settings])

  useEffect(() => {
    fetchRecipients()
    fetchApiKeys()
  }, [])

  const fetchRecipients = async () => {
    try {
      const res = await api.get('/settings/recipients')
      setRecipients(res.data)
    } catch {
      addToast('Failed to load recipients', 'error')
    } finally {
      setLoadingRecipients(false)
    }
  }

  const fetchApiKeys = async () => {
    try {
      const res = await api.get<ApiKeyStatus[]>('/settings/api-keys')
      setApiKeys(res.data)
    } catch {
      addToast('Failed to load API keys', 'error')
    } finally {
      setLoadingKeys(false)
    }
  }

  const save = async () => {
    try {
      await api.put('/settings', { timezone, log_level: logLevel })
      addToast('Settings saved', 'success')
    } catch {
      addToast('Failed to save', 'error')
    }
  }

  const addRecipient = async () => {
    const id = newChatId.trim()
    if (!id) return
    try {
      await api.post('/settings/recipients', { chat_id: id, label: newLabel.trim() })
      setNewChatId('')
      setNewLabel('')
      await fetchRecipients()
      addToast('Recipient added', 'success')
    } catch {
      addToast('Failed to add recipient', 'error')
    }
  }

  const removeRecipient = async (chatId: string) => {
    try {
      await api.delete(`/settings/recipients/${chatId}`)
      await fetchRecipients()
      addToast('Recipient removed', 'success')
    } catch {
      addToast('Failed to remove recipient', 'error')
    }
  }

  const testRecipient = async (chatId: string) => {
    setTestingId(chatId)
    try {
      const res = await api.post(`/settings/recipients/${chatId}/test`)
      if (res.data.success) {
        addToast('Test message sent!', 'success')
      } else {
        addToast(res.data.message || 'Test failed', 'error')
      }
    } catch {
      addToast('Failed to send test message', 'error')
    } finally {
      setTestingId(null)
    }
  }

  const saveApiKey = async (keyName: string) => {
    setSavingKey(keyName)
    try {
      await api.post('/settings/api-keys', { key: keyName, value: keyValue })
      addToast('API key saved', 'success')
      setEditingKey(null)
      setKeyValue('')
      await fetchApiKeys()
    } catch {
      addToast('Failed to save API key', 'error')
    } finally {
      setSavingKey(null)
    }
  }

  const removeApiKey = async (keyName: string) => {
    try {
      await api.delete(`/settings/api-keys/${keyName}`)
      addToast('API key removed', 'success')
      await fetchApiKeys()
    } catch {
      addToast('Failed to remove API key', 'error')
    }
  }

  const testApiKey = async (apiName: string) => {
    setTestingApi(apiName)
    try {
      const res = await api.post(`/onboarding/test/${apiName}`)
      setTestResults(prev => ({ ...prev, [apiName]: res.data }))
    } catch {
      setTestResults(prev => ({ ...prev, [apiName]: { success: false, message: 'Test failed' } }))
    } finally {
      setTestingApi(null)
    }
  }

  const exportConfig = () => {
    window.open('/api/settings/export', '_blank')
  }

  const importConfig = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await api.post('/settings/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      addToast(`Imported: ${res.data.imported.join(', ')}`, 'success')
    } catch {
      addToast('Import failed', 'error')
    }
    e.target.value = ''
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />

  // Group API keys by category
  const keysByCategory: Record<string, ApiKeyStatus[]> = {}
  for (const k of apiKeys) {
    if (!keysByCategory[k.category]) keysByCategory[k.category] = []
    keysByCategory[k.category].push(k)
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold mb-1">Settings</h1>
      <p className="text-apple-gray-400 text-sm mb-8">General configuration and API keys</p>

      <div className="card mb-6">
        <div className="space-y-6">
          <div>
            <label className="label">Timezone</label>
            <select className="input-field" value={timezone} onChange={e => setTimezone(e.target.value)}>
              {TIMEZONES.map(tz => (
                <option key={tz} value={tz}>{tz}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Log Level</label>
            <select className="input-field" value={logLevel} onChange={e => setLogLevel(e.target.value)}>
              {LOG_LEVELS.map(level => (
                <option key={level} value={level}>{level}</option>
              ))}
            </select>
          </div>

          <button onClick={save} className="btn-primary flex items-center gap-2">
            <Save size={14} /> Save Settings
          </button>
        </div>
      </div>

      {/* API Keys Management */}
      <div className="card mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Key size={18} className="text-apple-blue" />
          <h3 className="font-medium">API Keys</h3>
        </div>

        {loadingKeys ? (
          <LoadingSpinner size="sm" />
        ) : (
          <div className="space-y-6">
            {CATEGORY_ORDER.map(cat => {
              const catKeys = keysByCategory[cat]
              if (!catKeys) return null
              const catDef = CATEGORY_LABELS[cat]
              return (
                <div key={cat}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-apple-gray-500">{catDef.icon}</span>
                    <h4 className="text-sm font-semibold text-apple-gray-700">{catDef.label}</h4>
                    <span className="text-[10px] text-apple-gray-400">{catDef.description}</span>
                  </div>
                  <div className="space-y-2">
                    {catKeys.map(k => (
                      <div key={k.key} className="flex items-center gap-2 p-3 bg-apple-gray-50 rounded-lg">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-apple-gray-700">{k.label}</span>
                            {k.configured ? (
                              <span className="flex items-center gap-0.5 text-[10px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full">
                                <Check size={10} /> Active
                              </span>
                            ) : (
                              <span className="text-[10px] text-apple-gray-400 bg-apple-gray-100 px-1.5 py-0.5 rounded-full">
                                Not set
                              </span>
                            )}
                          </div>
                          {k.configured && k.masked_value && (
                            <span className="text-[10px] text-apple-gray-400 font-mono">{k.masked_value}</span>
                          )}
                          {/* Test result inline */}
                          {testResults[k.key] && (
                            <span className={`text-[10px] ml-2 ${testResults[k.key].success ? 'text-green-600' : 'text-red-500'}`}>
                              {testResults[k.key].message}
                            </span>
                          )}
                        </div>

                        {editingKey === k.key ? (
                          <div className="flex items-center gap-1.5">
                            <MaskedField
                              value={keyValue}
                              onChange={setKeyValue}
                              placeholder={`Enter ${k.label}`}
                            />
                            <button
                              onClick={() => saveApiKey(k.key)}
                              disabled={savingKey === k.key || !keyValue.trim()}
                              className="btn-primary text-xs px-2 py-1 flex items-center gap-1"
                            >
                              {savingKey === k.key ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
                              Save
                            </button>
                            <button
                              onClick={() => { setEditingKey(null); setKeyValue('') }}
                              className="text-apple-gray-400 hover:text-apple-gray-600 p-1"
                            >
                              <X size={14} />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1">
                            {k.configured && !['telegram_bot_token', 'telegram_chat_id'].includes(k.key) && (
                              <button
                                onClick={() => testApiKey(k.key)}
                                disabled={testingApi === k.key}
                                className="btn-secondary text-[10px] px-2 py-1 flex items-center gap-1"
                              >
                                {testingApi === k.key ? <Loader2 size={10} className="animate-spin" /> : null}
                                Test
                              </button>
                            )}
                            <button
                              onClick={() => { setEditingKey(k.key); setKeyValue('') }}
                              className="btn-secondary text-[10px] px-2 py-1"
                            >
                              {k.configured ? 'Change' : 'Set'}
                            </button>
                            {k.configured && (
                              <button
                                onClick={() => removeApiKey(k.key)}
                                className="text-red-400 hover:text-red-600 p-1"
                                title="Remove key"
                              >
                                <Trash2 size={12} />
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Telegram Recipients */}
      <div className="card mb-6">
        <h3 className="font-medium mb-4">Telegram Recipients</h3>

        {loadingRecipients ? (
          <LoadingSpinner size="sm" />
        ) : (
          <>
            {recipients.length > 0 && (
              <div className="space-y-2 mb-4">
                {recipients.map(r => (
                  <div key={r.chat_id} className="flex items-center gap-3 p-3 bg-apple-gray-50 dark:bg-apple-gray-800 rounded-lg">
                    <div className="flex-1 min-w-0">
                      <span className="font-mono text-sm">{r.chat_id}</span>
                      {r.label && (
                        <span className="ml-2 text-apple-gray-400 text-sm">({r.label})</span>
                      )}
                    </div>
                    <button
                      onClick={() => testRecipient(r.chat_id)}
                      disabled={testingId === r.chat_id}
                      className="btn-secondary text-xs px-2 py-1 flex items-center gap-1"
                    >
                      <Send size={12} />
                      {testingId === r.chat_id ? 'Sending...' : 'Test'}
                    </button>
                    <button
                      onClick={() => removeRecipient(r.chat_id)}
                      className="text-red-500 hover:text-red-600 p-1"
                      title="Remove recipient"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Chat ID"
                value={newChatId}
                onChange={e => setNewChatId(e.target.value)}
                className="input-field flex-1"
                onKeyDown={e => e.key === 'Enter' && addRecipient()}
              />
              <input
                type="text"
                placeholder="Label (optional)"
                value={newLabel}
                onChange={e => setNewLabel(e.target.value)}
                className="input-field flex-1"
                onKeyDown={e => e.key === 'Enter' && addRecipient()}
              />
              <button onClick={addRecipient} className="btn-primary flex items-center gap-1 px-3">
                <Plus size={14} /> Add
              </button>
            </div>

            <button
              onClick={() => setShowGuide(!showGuide)}
              className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-600 mt-3"
            >
              {showGuide ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              How to get a chat ID
            </button>

            {showGuide && (
              <div className="mt-3 p-4 bg-apple-gray-50 dark:bg-apple-gray-800 rounded-lg text-sm space-y-4">
                <div>
                  <p className="font-medium mb-1">Personal chat (DM)</p>
                  <ol className="list-decimal list-inside space-y-1 text-apple-gray-400">
                    <li>Open Telegram and search for <span className="font-mono text-xs">@userinfobot</span></li>
                    <li>Start/message the bot — it replies with your chat ID</li>
                    <li>Copy the numeric ID and paste it above</li>
                  </ol>
                </div>

                <div>
                  <p className="font-medium mb-1">Group</p>
                  <ol className="list-decimal list-inside space-y-1 text-apple-gray-400">
                    <li>Create a group in Telegram (or use an existing one)</li>
                    <li>Add your Market Digest bot to the group</li>
                    <li>Send any message in the group</li>
                    <li>Open this URL in your browser:{' '}
                      <span className="font-mono text-xs break-all">
                        https://api.telegram.org/bot&lt;YOUR_BOT_TOKEN&gt;/getUpdates
                      </span>
                    </li>
                    <li>Look for <span className="font-mono text-xs">"chat":&#123;"id":-XXXXXXXXX&#125;</span> — the negative number is the group chat ID</li>
                  </ol>
                </div>

                <div>
                  <p className="font-medium mb-1">Channel</p>
                  <ol className="list-decimal list-inside space-y-1 text-apple-gray-400">
                    <li>Create a channel in Telegram (or use an existing one)</li>
                    <li>Go to channel Settings &rarr; Administrators &rarr; add your bot as admin</li>
                    <li>The bot needs at least "Post Messages" permission</li>
                    <li>Post any message in the channel</li>
                    <li>Visit the same <span className="font-mono text-xs">getUpdates</span> URL above</li>
                    <li>The channel chat ID is usually <span className="font-mono text-xs">-100XXXXXXXXX</span></li>
                  </ol>
                </div>

                <p className="text-xs text-apple-gray-400 italic">
                  Tip: After adding the ID here, click "Test" to verify the bot can send to that chat.
                </p>
              </div>
            )}
          </>
        )}
      </div>

      <div className="card">
        <h3 className="font-medium mb-4">Backup & Restore</h3>
        <div className="flex flex-col sm:flex-row gap-3">
          <button onClick={exportConfig} className="btn-secondary flex items-center gap-2">
            <Download size={14} /> Export Config
          </button>
          <label className="btn-secondary flex items-center gap-2 cursor-pointer">
            <Upload size={14} /> Import Config
            <input type="file" accept=".zip" className="hidden" onChange={importConfig} />
          </label>
        </div>
        <p className="text-xs text-apple-gray-400 mt-3">
          Export downloads a zip of .env, instruments.yaml, prompts.yaml, and digests.yaml.
          Import replaces these files from a previously exported zip.
        </p>
      </div>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
