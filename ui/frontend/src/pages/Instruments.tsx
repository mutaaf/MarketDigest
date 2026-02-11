import { useState } from 'react'
import { Search, Plus, Trash2, X } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import api from '../api/client'
import type { Instrument } from '../api/types'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ToastContainer from '../components/common/Toast'

const CATEGORIES = ['All', 'forex', 'forex_index', 'us_index', 'us_futures', 'metals', 'energy', 'agriculture', 'crypto']
const CATEGORY_LABELS: Record<string, string> = {
  All: 'All',
  forex: 'Forex',
  forex_index: 'Forex Index',
  us_index: 'US Indices',
  us_futures: 'US Futures',
  metals: 'Metals',
  energy: 'Energy',
  agriculture: 'Agriculture',
  crypto: 'Crypto',
}

export default function Instruments() {
  const { data: instruments, loading, refetch } = useApi<Instrument[]>('/instruments')
  const { toasts, addToast, removeToast } = useToast()
  const [activeTab, setActiveTab] = useState('All')
  const [search, setSearch] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [newInstrument, setNewInstrument] = useState({ symbol: '', yfinance: '', name: '', category: 'crypto', subcategory: '' })

  const toggleInstrument = async (cat: string, symbol: string, enabled: boolean) => {
    try {
      await api.put(`/instruments/${cat}/${symbol}/toggle`, { enabled })
      refetch()
    } catch {
      addToast('Failed to toggle instrument', 'error')
    }
  }

  const addInstrument = async () => {
    try {
      await api.post('/instruments', newInstrument)
      addToast(`Added ${newInstrument.name}`, 'success')
      setShowAddModal(false)
      setNewInstrument({ symbol: '', yfinance: '', name: '', category: 'crypto', subcategory: '' })
      refetch()
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to add', 'error')
    }
  }

  const deleteInstrument = async (cat: string, symbol: string) => {
    try {
      await api.delete(`/instruments/${cat}/${symbol}`)
      addToast(`Deleted ${symbol}`, 'success')
      refetch()
    } catch {
      addToast('Failed to delete', 'error')
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />

  const filtered = (instruments || []).filter(i => {
    if (activeTab !== 'All' && i.category !== activeTab) return false
    if (search) {
      const q = search.toLowerCase()
      return i.name.toLowerCase().includes(q) || i.symbol.toLowerCase().includes(q) || i.yfinance.toLowerCase().includes(q)
    }
    return true
  })

  return (
    <div className="max-w-5xl">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Instruments</h1>
          <p className="text-apple-gray-400 text-sm mt-1">{instruments?.length ?? 0} instruments configured</p>
        </div>
        <button onClick={() => setShowAddModal(true)} className="btn-primary flex items-center gap-2">
          <Plus size={14} /> Add Instrument
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 overflow-x-auto whitespace-nowrap pb-1 -mx-1 px-1">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveTab(cat)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === cat ? 'bg-apple-blue text-white' : 'bg-white text-apple-gray-500 hover:bg-apple-gray-200'
            }`}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-apple-gray-400" />
        <input
          type="text"
          className="input-field pl-9"
          placeholder="Search instruments..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Desktop Table */}
      <div className="hidden md:block card !p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-apple-gray-400 uppercase tracking-wide bg-apple-gray-50">
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Symbol</th>
              <th className="px-4 py-3">yFinance</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3 text-center">Enabled</th>
              <th className="px-4 py-3 w-10"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(inst => (
              <tr key={`${inst.category}-${inst.symbol}`} className="border-t border-apple-gray-100 hover:bg-apple-gray-50">
                <td className="px-4 py-3 font-medium">{inst.name}</td>
                <td className="px-4 py-3 text-apple-gray-500">{inst.symbol}</td>
                <td className="px-4 py-3 text-apple-gray-400 font-mono text-xs">{inst.yfinance}</td>
                <td className="px-4 py-3">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-apple-gray-100 text-apple-gray-500">
                    {CATEGORY_LABELS[inst.category] || inst.category}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => toggleInstrument(inst.category, inst.symbol, !inst.enabled)}
                    className={`w-10 h-6 rounded-full relative transition-colors ${inst.enabled ? 'bg-apple-green' : 'bg-apple-gray-300'}`}
                  >
                    <div className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${inst.enabled ? 'left-5' : 'left-1'}`} />
                  </button>
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => deleteInstrument(inst.category, inst.symbol)}
                    className="text-apple-gray-300 hover:text-apple-red transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="text-center py-8 text-apple-gray-400 text-sm">No instruments found</p>
        )}
      </div>

      {/* Mobile Card List */}
      <div className="md:hidden space-y-2">
        {filtered.map(inst => (
          <div key={`m-${inst.category}-${inst.symbol}`} className="card !p-3 flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{inst.name}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-apple-gray-400">{inst.symbol}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-apple-gray-100 text-apple-gray-500">
                  {CATEGORY_LABELS[inst.category] || inst.category}
                </span>
              </div>
            </div>
            <button
              onClick={() => toggleInstrument(inst.category, inst.symbol, !inst.enabled)}
              className={`w-10 h-6 rounded-full relative transition-colors flex-shrink-0 ${inst.enabled ? 'bg-apple-green' : 'bg-apple-gray-300'}`}
            >
              <div className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${inst.enabled ? 'left-5' : 'left-1'}`} />
            </button>
            <button
              onClick={() => deleteInstrument(inst.category, inst.symbol)}
              className="text-apple-gray-300 hover:text-apple-red transition-colors flex-shrink-0"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="text-center py-8 text-apple-gray-400 text-sm">No instruments found</p>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/30 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4" onClick={() => setShowAddModal(false)}>
          <div className="card w-full sm:max-w-md rounded-b-none sm:rounded-b-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium">Add Instrument</h3>
              <button onClick={() => setShowAddModal(false)} className="text-apple-gray-400 hover:text-apple-gray-600">
                <X size={18} />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="label">Name</label>
                <input className="input-field" value={newInstrument.name} onChange={e => setNewInstrument(prev => ({ ...prev, name: e.target.value }))} placeholder="e.g. Bitcoin" />
              </div>
              <div>
                <label className="label">Symbol</label>
                <input className="input-field" value={newInstrument.symbol} onChange={e => setNewInstrument(prev => ({ ...prev, symbol: e.target.value }))} placeholder="e.g. BTC" />
              </div>
              <div>
                <label className="label">yFinance Ticker</label>
                <input className="input-field" value={newInstrument.yfinance} onChange={e => setNewInstrument(prev => ({ ...prev, yfinance: e.target.value }))} placeholder="e.g. BTC-USD" />
              </div>
              <div>
                <label className="label">Category</label>
                <select className="input-field" value={newInstrument.category} onChange={e => setNewInstrument(prev => ({ ...prev, category: e.target.value }))}>
                  {CATEGORIES.filter(c => c !== 'All').map(cat => (
                    <option key={cat} value={cat}>{CATEGORY_LABELS[cat]}</option>
                  ))}
                </select>
              </div>
              <button onClick={addInstrument} className="btn-primary w-full" disabled={!newInstrument.symbol || !newInstrument.yfinance || !newInstrument.name}>
                Add Instrument
              </button>
            </div>
          </div>
        </div>
      )}

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
