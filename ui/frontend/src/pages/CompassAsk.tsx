// Compass — Ask: a portfolio-aware assistant that explains, in plain English.
// Conversations persist per portfolio and answers keep arriving even if you
// navigate away mid-question (see chatStore).
import { FormEvent, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Send, Compass, BookOpen, Plus, Check, Trash2 } from 'lucide-react'
import api from '../api/client'
import { usePortfolioSelection } from '../components/compass/ui'
import { clearChat, sendMessage, useChat } from '../components/compass/chatStore'

const SUGGESTIONS = [
  'How is my portfolio doing?',
  'Am I diversified enough?',
  'Compare VOO and VTI',
  'What should I do with my cash?',
  'What is an expense ratio?',
]

export default function CompassAsk() {
  const { portfolios, selected } = usePortfolioSelection()
  const [params] = useSearchParams()
  const { messages, busy, error } = useChat(selected)
  const [input, setInput] = useState('')
  const [savedTopics, setSavedTopics] = useState<Set<string>>(new Set())
  const [confirmClear, setConfirmClear] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const autoSent = useRef(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, busy])

  // Deep links (?q=...) fire once the portfolio selection settles
  useEffect(() => {
    const q = params.get('q')
    if (q && !autoSent.current && portfolios !== null) {
      autoSent.current = true
      sendMessage(selected, q)
    }
  }, [params, portfolios, selected])

  const saveTopic = async (term: string, context: string) => {
    if (!selected) return
    setSavedTopics(prev => new Set(prev).add(term))
    try {
      await api.post(`/portfolio/${selected}/learn`, { term, context: context.slice(0, 500) }, { timeout: 60000 })
    } catch {
      setSavedTopics(prev => { const next = new Set(prev); next.delete(term); return next })
    }
  }

  return (
    <div className="flex min-h-[70vh] flex-col">
      {messages.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center py-10 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-apple-blue/10">
            <Compass size={26} className="text-apple-blue" />
          </div>
          <h1 className="mt-4 text-lg font-bold text-apple-gray-800">Ask Compass anything</h1>
          <p className="mx-auto mt-1 max-w-xs text-sm text-apple-gray-500">
            It knows your portfolio and today's market data, and it explains everything in plain English.
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            {SUGGESTIONS.map(s => (
              <button key={s} onClick={() => sendMessage(selected, s)}
                className="min-h-[40px] rounded-full border border-apple-gray-200 bg-white px-4 text-sm text-apple-gray-600 active:bg-apple-gray-100">
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {messages.length > 0 && (
        <div className="flex-1 space-y-3 pb-4">
          <div className="flex justify-end">
            {confirmClear ? (
              <span className="flex items-center gap-2 text-xs text-apple-gray-500">
                Clear this conversation?
                <button onClick={() => setConfirmClear(false)} className="min-h-[36px] rounded-lg px-2 font-medium">Keep</button>
                <button onClick={() => { clearChat(selected); setConfirmClear(false) }}
                  className="min-h-[36px] rounded-lg bg-apple-red px-3 font-semibold text-white">Clear</button>
              </span>
            ) : (
              <button onClick={() => setConfirmClear(true)}
                className="flex min-h-[36px] items-center gap-1.5 rounded-lg px-2 text-xs text-apple-gray-400 active:text-apple-red">
                <Trash2 size={12} /> New chat
              </button>
            )}
          </div>
          {messages.map((m, i) => (
            <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'rounded-br-md bg-apple-blue text-white'
                  : 'rounded-bl-md border border-apple-gray-200 bg-white text-apple-gray-700'
              }`}>
                {m.content}
              </div>
              {m.role === 'assistant' && (m.topics?.length ?? 0) > 0 && (
                <div className="mt-1.5 flex max-w-[85%] flex-wrap items-center gap-1.5">
                  <BookOpen size={12} className="text-apple-gray-300" />
                  {m.topics!.map(t => (
                    <button key={t} onClick={() => saveTopic(t, m.content)} disabled={savedTopics.has(t)}
                      className={`flex min-h-[32px] items-center gap-1 rounded-full px-2.5 text-[11px] font-medium ${
                        savedTopics.has(t)
                          ? 'bg-apple-green/10 text-green-700'
                          : 'border border-apple-gray-200 bg-white text-apple-gray-500 active:bg-apple-gray-100'
                      }`}>
                      {savedTopics.has(t) ? <Check size={10} /> : <Plus size={10} />}
                      {savedTopics.has(t) ? `In Learn: ${t}` : `Learn: ${t}`}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          {busy && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-md border border-apple-gray-200 bg-white px-4 py-3">
                <span className="inline-flex gap-1">
                  {[0, 1, 2].map(i => (
                    <span key={i} className="h-1.5 w-1.5 animate-bounce rounded-full bg-apple-gray-300"
                      style={{ animationDelay: `${i * 150}ms` }} />
                  ))}
                </span>
              </div>
            </div>
          )}
          {error && (
            <div className="rounded-xl border border-apple-red/20 bg-apple-red/5 px-4 py-2.5 text-sm text-apple-gray-700">
              {error}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input bar */}
      <form
        onSubmit={(e: FormEvent) => { e.preventDefault(); sendMessage(selected, input); setInput('') }}
        className="sticky flex gap-2 border-t border-apple-gray-200 bg-apple-gray-100 py-3 md:bottom-0"
        style={{ bottom: 'calc(4rem + env(safe-area-inset-bottom, 0px))' }}
      >
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about your money…"
          className="min-h-[48px] flex-1 rounded-2xl border border-apple-gray-200 bg-white px-4 text-sm text-apple-gray-800 focus:border-apple-blue focus:outline-none"
        />
        <button type="submit" disabled={busy || !input.trim()}
          className="flex min-h-[48px] min-w-[48px] items-center justify-center rounded-2xl bg-apple-blue text-white active:opacity-80 disabled:opacity-40">
          <Send size={18} />
        </button>
      </form>
      <p className="pb-2 text-center text-[10px] text-apple-gray-400">
        Educational only — Compass isn't a licensed financial advisor.
      </p>
    </div>
  )
}
