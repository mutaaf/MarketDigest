import { useState } from 'react'
import { Loader2, Wifi, WifiOff } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import api from '../api/client'
import type { DataSource, CacheStats, TestResult } from '../api/types'
import StatusDot from '../components/common/StatusDot'
import MaskedField from '../components/common/MaskedField'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ToastContainer from '../components/common/Toast'

export default function DataSources() {
  const { data: sources, loading, refetch } = useApi<DataSource[]>('/sources')
  const { data: cacheStats, refetch: refetchCache } = useApi<CacheStats>('/cache/stats')
  const { toasts, addToast, removeToast } = useToast()
  const [testing, setTesting] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({})
  const [editingKey, setEditingKey] = useState<Record<string, string>>({})

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

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold mb-1">Data Sources</h1>
      <p className="text-apple-gray-400 text-sm mb-8">Manage API connections and cache</p>

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

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
