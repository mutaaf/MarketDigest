// Compass client-storage manager — everything we persist lives under
// 'compass.*' keys with a hard budget and automatic garbage collection.

const BUDGET_BYTES = 10 * 1024 * 1024  // ~10MB (browser quota territory)
const CHAT_PREFIX = 'compass.chat.'
const DEFS_KEY = 'compass.defs.v2'

export function compassStorageBytes(): number {
  let bytes = 0
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith('compass.')) {
      bytes += (key.length + (localStorage.getItem(key)?.length ?? 0)) * 2 // UTF-16
    }
  }
  return bytes
}

/** Reclaim space, gentlest first: trim chats → prune definitions (LRU) →
 * drop oldest whole chats. Safe to call often; no-ops under budget. */
export function gcStorage(): void {
  try {
    if (compassStorageBytes() < BUDGET_BYTES) return

    // 1) Trim every chat to its most recent 20 messages
    for (const key of chatKeys()) {
      const data = readJson<{ messages: unknown[]; updated: number }>(key)
      if (data?.messages && data.messages.length > 20) {
        localStorage.setItem(key, JSON.stringify({ ...data, messages: data.messages.slice(-20) }))
      }
    }
    if (compassStorageBytes() < BUDGET_BYTES) return

    // 2) Keep only the 150 most recently used term definitions
    const defs = readJson<Record<string, { t: string; ts: number }>>(DEFS_KEY)
    if (defs) {
      const entries = Object.entries(defs).sort((a, b) => b[1].ts - a[1].ts).slice(0, 150)
      localStorage.setItem(DEFS_KEY, JSON.stringify(Object.fromEntries(entries)))
    }
    if (compassStorageBytes() < BUDGET_BYTES) return

    // 3) Drop whole chats, oldest first, until under budget
    const chats = chatKeys()
      .map(key => ({ key, updated: readJson<{ updated: number }>(key)?.updated ?? 0 }))
      .sort((a, b) => a.updated - b.updated)
    for (const c of chats) {
      if (compassStorageBytes() < BUDGET_BYTES) break
      localStorage.removeItem(c.key)
    }
  } catch { /* storage APIs can throw in private mode — never crash the app */ }
}

function chatKeys(): string[] {
  const keys: string[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith(CHAT_PREFIX)) keys.push(key)
  }
  return keys
}

export function readJson<T>(key: string): T | null {
  try { return JSON.parse(localStorage.getItem(key) || 'null') } catch { return null }
}

export function writeJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    gcStorage()  // quota hit — reclaim and retry once
    try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* give up quietly */ }
  }
}
