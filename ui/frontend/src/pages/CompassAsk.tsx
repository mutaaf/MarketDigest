// Compass — Ask: a portfolio-aware assistant that explains, in plain English.
import { FormEvent, useEffect, useRef, useState } from 'react'
import { Send, Compass } from 'lucide-react'
import api from '../api/client'
import { usePortfolioSelection } from '../components/compass/ui'

interface Msg {
  role: 'user' | 'assistant'
  content: string
}

const SUGGESTIONS = [
  'How is my portfolio doing?',
  'Am I diversified enough?',
  'Compare VOO and VTI',
  'What should I do with my cash?',
  'What is an expense ratio?',
]

export default function CompassAsk() {
  const { selected } = usePortfolioSelection()
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  const send = async (text: string) => {
    const question = text.trim()
    if (!question || busy) return
    const next: Msg[] = [...messages, { role: 'user', content: question }]
    setMessages(next)
    setInput('')
    setBusy(true)
    setError(null)
    try {
      const res = await api.post<{ reply: string }>('/assistant/chat', {
        portfolio: selected || null,
        messages: next.slice(-12),
      }, { timeout: 120000 })
      setMessages([...next, { role: 'assistant', content: res.data.reply }])
    } catch (err: any) {
      setError(err.response?.data?.detail ||
        "Compass couldn't answer just now. Check your connection and try again.")
    } finally {
      setBusy(false)
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
              <button key={s} onClick={() => send(s)}
                className="min-h-[40px] rounded-full border border-apple-gray-200 bg-white px-4 text-sm text-apple-gray-600 active:bg-apple-gray-100">
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {messages.length > 0 && (
        <div className="flex-1 space-y-3 pb-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'rounded-br-md bg-apple-blue text-white'
                  : 'rounded-bl-md border border-apple-gray-200 bg-white text-apple-gray-700'
              }`}>
                {m.content}
              </div>
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
        onSubmit={(e: FormEvent) => { e.preventDefault(); send(input) }}
        className="sticky bottom-16 flex gap-2 border-t border-apple-gray-200 bg-apple-gray-100 py-3 md:bottom-0"
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
