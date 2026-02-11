import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Play, Send, Code, Eye, Loader2, LayoutGrid } from 'lucide-react'
import { useToast } from '../hooks/useToast'
import api from '../api/client'
import ToastContainer from '../components/common/Toast'
import DigestViewer from '../components/run/DigestViewer'

type ViewMode = 'rich' | 'telegram' | 'raw'

export default function RunPreview() {
  const location = useLocation()
  const { toasts, addToast, removeToast } = useToast()
  const [digestType, setDigestType] = useState('morning')
  const [mode, setMode] = useState('facts')
  const [actionItems, setActionItems] = useState(false)
  const [running, setRunning] = useState(false)
  const [sending, setSending] = useState(false)
  const [sendingActionItems, setSendingActionItems] = useState(false)
  const [content, setContent] = useState('')
  const [actionItemsContent, setActionItemsContent] = useState('')
  const [messageCount, setMessageCount] = useState(0)
  const [actionItemsMessageCount, setActionItemsMessageCount] = useState(0)
  const [viewMode, setViewMode] = useState<ViewMode>('rich')

  // Accept content from dashboard quick run
  useEffect(() => {
    const state = location.state as any
    if (state?.content) {
      setContent(state.content)
      setDigestType(state.type || 'morning')
    }
  }, [location])

  const runDigest = async () => {
    setRunning(true)
    setContent('')
    setActionItemsContent('')
    try {
      const res = await api.post('/digests/run', {
        digest_type: digestType,
        mode,
        dry_run: true,
        action_items: actionItems,
      })
      if (res.data.success) {
        setContent(res.data.content)
        setMessageCount(res.data.message_count)
        let toastMsg = `Digest generated (${res.data.message_count} messages, ${res.data.total_length} chars)`
        if (res.data.action_items_content) {
          setActionItemsContent(res.data.action_items_content)
          setActionItemsMessageCount(res.data.action_items_message_count)
          toastMsg += ` + Action Items (${res.data.action_items_length} chars)`
        }
        addToast(toastMsg, 'success')
      }
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Digest run failed', 'error')
    } finally {
      setRunning(false)
    }
  }

  const sendToTelegram = async (contentToSend: string, label: string, setLoadingFn: (v: boolean) => void) => {
    if (!contentToSend) return
    setLoadingFn(true)
    try {
      const res = await api.post('/digests/send', { content: contentToSend })
      if (res.data.success) {
        addToast(`${label} sent to Telegram!`, 'success')
      } else {
        addToast(res.data.message || `Failed to send ${label}`, 'error')
      }
    } catch (err: any) {
      addToast(err.response?.data?.detail || `Send ${label} failed`, 'error')
    } finally {
      setLoadingFn(false)
    }
  }

  const sendAll = async () => {
    await sendToTelegram(content, 'Digest', setSending)
    if (actionItemsContent) {
      await new Promise(r => setTimeout(r, 2000))
      await sendToTelegram(actionItemsContent, 'Action Items', setSendingActionItems)
    }
  }

  const viewModes: { key: ViewMode; label: string; icon: React.ReactNode }[] = [
    { key: 'rich', label: 'Rich', icon: <LayoutGrid size={12} /> },
    { key: 'telegram', label: 'Telegram', icon: <Eye size={12} /> },
    { key: 'raw', label: 'Raw', icon: <Code size={12} /> },
  ]

  const renderPreviewContent = (previewContent: string) => {
    if (viewMode === 'rich') {
      return <DigestViewer content={previewContent} />
    }
    if (viewMode === 'telegram') {
      return (
        <div className="card !bg-gray-900 !border-gray-700">
          <div
            className="text-gray-100 max-h-[70vh] overflow-auto font-sans text-sm leading-relaxed"
            style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}
            dangerouslySetInnerHTML={{ __html: previewContent }}
          />
        </div>
      )
    }
    return (
      <div className="card">
        <pre className="bg-apple-gray-50 rounded-lg p-4 md:p-6 text-xs font-mono overflow-auto max-h-[70vh] whitespace-pre-wrap break-words">
          {previewContent}
        </pre>
      </div>
    )
  }

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-semibold mb-1">Run & Preview</h1>
      <p className="text-apple-gray-400 text-sm mb-6">Generate digests and preview before sending</p>

      {/* Controls */}
      <div className="card mb-6">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
          <div>
            <label className="label">Digest Type</label>
            <select
              className="input-field w-full sm:!w-40"
              value={digestType}
              onChange={e => setDigestType(e.target.value)}
            >
              <option value="morning">Morning</option>
              <option value="afternoon">Afternoon</option>
              <option value="weekly">Weekly</option>
              <option value="daytrade">Day Trade</option>
            </select>
          </div>
          <div>
            <label className="label">Mode</label>
            <select
              className="input-field w-full sm:!w-32"
              value={mode}
              onChange={e => setMode(e.target.value)}
            >
              <option value="facts">Facts Only</option>
              <option value="full">Full (+ LLM)</option>
              <option value="both">Both</option>
            </select>
          </div>
          <div className="flex items-center gap-2 sm:mt-5">
            <input
              type="checkbox"
              id="action-items"
              checked={actionItems}
              onChange={e => setActionItems(e.target.checked)}
              className="rounded border-apple-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="action-items" className="text-sm text-apple-gray-600 select-none">
              Include Action Items
            </label>
          </div>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-3 sm:mt-0 mt-1">
            <button
              onClick={runDigest}
              disabled={running}
              className="btn-primary flex items-center justify-center gap-2"
            >
              {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              {running ? 'Generating...' : 'Run Digest'}
            </button>
            <button
              onClick={sendAll}
              disabled={!content || sending || sendingActionItems}
              className="btn-secondary flex items-center justify-center gap-2"
            >
              {(sending || sendingActionItems) ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
              Send to Telegram
            </button>
          </div>
        </div>
        {running && (
          <div className="mt-4 text-sm text-apple-gray-400">
            Building digest... This may take 30-60 seconds if LLM analysis is enabled.
          </div>
        )}
      </div>

      {/* Preview */}
      {content && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <h3 className="font-medium">Preview</h3>
              <span className="text-xs text-apple-gray-400">
                {content.length} chars | {messageCount} message(s)
              </span>
            </div>

            {/* Segmented control */}
            <div className="inline-flex rounded-lg border border-apple-gray-200 bg-apple-gray-50 p-0.5">
              {viewModes.map(vm => (
                <button
                  key={vm.key}
                  onClick={() => setViewMode(vm.key)}
                  className={`flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                    viewMode === vm.key
                      ? 'bg-white text-apple-gray-800 shadow-sm'
                      : 'text-apple-gray-500 hover:text-apple-gray-700'
                  }`}
                >
                  {vm.icon}
                  {vm.label}
                </button>
              ))}
            </div>
          </div>

          {renderPreviewContent(content)}
        </div>
      )}

      {/* Action Items Preview */}
      {actionItemsContent && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <h3 className="font-medium">Action Items</h3>
              <span className="text-xs text-apple-gray-400">
                {actionItemsContent.length} chars | {actionItemsMessageCount} message(s)
              </span>
            </div>
            <button
              onClick={() => sendToTelegram(actionItemsContent, 'Action Items', setSendingActionItems)}
              disabled={sendingActionItems}
              className="btn-secondary flex items-center gap-2 text-xs py-1.5 px-3"
            >
              {sendingActionItems ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
              Send Action Items Only
            </button>
          </div>

          {renderPreviewContent(actionItemsContent)}
        </div>
      )}

      {!content && !running && (
        <div className="card text-center py-16">
          <p className="text-apple-gray-400">Click "Run Digest" to generate a preview</p>
        </div>
      )}

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
