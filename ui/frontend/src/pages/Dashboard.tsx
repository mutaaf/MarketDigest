import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, Play, AlertCircle } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import api from '../api/client'
import type { ApiStatus } from '../api/types'
import StatusDot from '../components/common/StatusDot'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ToastContainer from '../components/common/Toast'

export default function Dashboard() {
  const { data: status, loading, refetch } = useApi<ApiStatus>('/status')
  const { toasts, addToast, removeToast } = useToast()
  const [runningDigest, setRunningDigest] = useState<string | null>(null)
  const navigate = useNavigate()

  const runQuickDigest = async (type: string) => {
    setRunningDigest(type)
    try {
      const res = await api.post('/digests/run', { digest_type: type, mode: 'facts', dry_run: true })
      if (res.data.success) {
        addToast(`${type} digest generated (${res.data.message_count} messages)`, 'success')
        navigate('/run', { state: { content: res.data.content, type } })
      }
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Digest run failed', 'error')
    } finally {
      setRunningDigest(null)
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />

  if (!status) return (
    <div className="flex items-center gap-3 text-apple-red mt-20 justify-center">
      <AlertCircle size={20} />
      <span>Failed to load status</span>
    </div>
  )

  if (!status.onboarding_complete) {
    return (
      <div className="max-w-lg mx-auto mt-20 text-center">
        <h2 className="text-2xl font-semibold mb-4">Welcome to Market Digest</h2>
        <p className="text-apple-gray-500 mb-6">
          Let's set up your API keys and configure your first digest.
        </p>
        <button onClick={() => navigate('/onboarding')} className="btn-primary text-base px-8 py-3">
          Start Setup
        </button>
      </div>
    )
  }

  const apiEntries = Object.entries(status.apis)

  return (
    <div className="max-w-6xl">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-8">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-apple-gray-400 text-sm mt-1">System overview and quick actions</p>
        </div>
        <button onClick={refetch} className="btn-secondary flex items-center gap-2">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* API Health Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
        {apiEntries.map(([key, info]) => (
          <div key={key} className="card !p-4 flex items-center gap-3">
            <StatusDot status={info.configured ? 'green' : 'gray'} size="md" />
            <div className="min-w-0">
              <p className="text-xs font-medium text-apple-gray-800 truncate">{info.name}</p>
              <p className="text-[11px] text-apple-gray-400">
                {info.configured ? 'Connected' : 'Not configured'}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {['morning', 'afternoon', 'weekly'].map(type => (
          <button
            key={type}
            onClick={() => runQuickDigest(type)}
            disabled={runningDigest !== null}
            className="card !p-6 hover:border-apple-blue transition-colors text-left group"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-apple-blue/10 flex items-center justify-center group-hover:bg-apple-blue/20 transition-colors">
                <Play size={18} className="text-apple-blue" />
              </div>
              <div>
                <p className="font-medium capitalize">{type} Digest</p>
                <p className="text-xs text-apple-gray-400">Quick run (facts only)</p>
              </div>
            </div>
            {runningDigest === type && <LoadingSpinner size="sm" className="mt-2" />}
          </button>
        ))}
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="card !p-4">
          <p className="text-xs text-apple-gray-400 uppercase tracking-wide">Cache Files</p>
          <p className="text-2xl font-semibold mt-1">{status.cache.file_count}</p>
          <p className="text-xs text-apple-gray-400">{(status.cache.total_size_bytes / 1024).toFixed(1)} KB</p>
        </div>
        <div className="card !p-4">
          <p className="text-xs text-apple-gray-400 uppercase tracking-wide">LLM Status</p>
          <p className="text-2xl font-semibold mt-1">{status.has_llm_key ? 'Ready' : 'No Keys'}</p>
          <p className="text-xs text-apple-gray-400">{status.has_llm_key ? 'Analysis available' : 'Facts-only mode'}</p>
        </div>
        <div className="card !p-4">
          <p className="text-xs text-apple-gray-400 uppercase tracking-wide">Timezone</p>
          <p className="text-2xl font-semibold mt-1">{status.timezone}</p>
          <p className="text-xs text-apple-gray-400">Log level: {status.log_level}</p>
        </div>
      </div>

      {/* Recent History */}
      {status.recent_history.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-medium text-apple-gray-800 mb-4">Recent Runs</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-apple-gray-400 uppercase tracking-wide">
                  <th className="pb-2 hidden sm:table-cell">Time</th>
                  <th className="pb-2">Type</th>
                  <th className="pb-2">Mode</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2 hidden sm:table-cell">Messages</th>
                </tr>
              </thead>
              <tbody>
                {status.recent_history.slice().reverse().map((entry, i) => (
                  <tr key={i} className="border-t border-apple-gray-100">
                    <td className="py-2 text-apple-gray-500 hidden sm:table-cell">
                      {new Date(entry.timestamp).toLocaleString()}
                    </td>
                    <td className="py-2 capitalize">{entry.type}</td>
                    <td className="py-2">{entry.mode}</td>
                    <td className="py-2">
                      <StatusDot status={entry.success ? 'green' : 'red'} />
                      <span className="ml-2">{entry.success ? 'Success' : 'Failed'}</span>
                    </td>
                    <td className="py-2 hidden sm:table-cell">{entry.message_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
