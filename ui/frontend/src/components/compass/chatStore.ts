// Ask chat store — lives OUTSIDE React so an in-flight answer keeps going
// and lands even if the user navigates away; conversations persist per
// portfolio and stay compact (capped history, trimmed persistence).
import { useSyncExternalStore } from 'react'
import api from '../../api/client'
import { gcStorage, readJson, writeJson } from './storage'

export interface ChatMsg {
  role: 'user' | 'assistant'
  content: string
  topics?: string[]
}

export interface ChatState {
  messages: ChatMsg[]
  busy: boolean
  error: string | null
}

const MAX_KEPT = 40          // messages persisted per conversation
const SENT_WINDOW = 12       // messages sent to the model per turn

const states = new Map<string, ChatState>()
const listeners = new Set<() => void>()

const key = (slug: string) => `compass.chat.${slug || 'none'}`

function notify() { listeners.forEach(l => l()) }

function getState(slug: string): ChatState {
  let s = states.get(slug)
  if (!s) {
    const saved = readJson<{ messages: ChatMsg[] }>(key(slug))
    s = { messages: saved?.messages ?? [], busy: false, error: null }
    states.set(slug, s)
  }
  return s
}

function setState(slug: string, patch: Partial<ChatState>) {
  const next = { ...getState(slug), ...patch }
  states.set(slug, next)
  if (patch.messages) {
    writeJson(key(slug), { messages: next.messages.slice(-MAX_KEPT), updated: Date.now() })
    gcStorage()
  }
  notify()
}

export function sendMessage(slug: string, text: string) {
  const question = text.trim()
  const s = getState(slug)
  if (!question || s.busy) return
  const messages: ChatMsg[] = [...s.messages, { role: 'user', content: question }]
  setState(slug, { messages, busy: true, error: null })

  api.post<{ reply: string; suggested_topics?: string[] }>('/assistant/chat', {
    portfolio: slug || null,
    messages: messages.slice(-SENT_WINDOW).map(({ role, content }) => ({ role, content })),
  }, { timeout: 120000 })
    .then(res => {
      setState(slug, {
        messages: [...getState(slug).messages,
          { role: 'assistant', content: res.data.reply, topics: res.data.suggested_topics }],
        busy: false,
      })
    })
    .catch(err => {
      setState(slug, {
        busy: false,
        error: err.response?.data?.detail ||
          "Compass couldn't answer just now. Your question is saved — try again.",
      })
    })
}

export function clearChat(slug: string) {
  states.set(slug, { messages: [], busy: false, error: null })
  try { localStorage.removeItem(key(slug)) } catch { /* fine */ }
  notify()
}

export function useChat(slug: string): ChatState {
  return useSyncExternalStore(
    listener => { listeners.add(listener); return () => listeners.delete(listener) },
    () => getState(slug),
  )
}
