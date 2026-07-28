// Smart import — bring holdings in from a screenshot, pasted text, or CSV.
// Extraction never saves directly: the user reviews editable rows first.
import { ClipboardEvent, useState } from 'react'
import { Camera, ClipboardPaste, FileText, Trash2, Upload } from 'lucide-react'
import api from '../../api/client'
import { inputCls, primaryBtn } from './ui'

interface DraftRow {
  symbol: string
  shares: string
  cost_basis: string
}

interface ExtractResponse {
  holdings: { symbol: string; shares: number; cost_basis: number }[]
  warnings: string[]
  source: string
  error?: string
}

type Mode = 'photo' | 'paste' | 'csv'

export default function SmartImport({ slug, onDone }: { slug: string; onDone: (count: number) => void }) {
  const [mode, setMode] = useState<Mode>('photo')
  const [rows, setRows] = useState<DraftRow[] | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [text, setText] = useState('')
  const [imagePreview, setImagePreview] = useState<string | null>(null)

  const extract = async (payload: { image_base64?: string; media_type?: string; text?: string }) => {
    setBusy(true)
    setErr(null)
    try {
      const res = await api.post<ExtractResponse>('/compass/extract-holdings', payload, { timeout: 120000 })
      if (res.data.error) {
        setErr(res.data.error)
      } else {
        setRows(res.data.holdings.map(h => ({
          symbol: h.symbol,
          shares: String(h.shares),
          cost_basis: h.cost_basis ? String(h.cost_basis) : '',
        })))
        setWarnings(res.data.warnings)
      }
    } catch (error: any) {
      setErr(error.response?.data?.detail || "Couldn't read that. Check your connection and try again.")
    } finally {
      setBusy(false)
    }
  }

  const onImage = (file: File | undefined | null) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setErr('That file isn’t an image — choose a screenshot (PNG or JPEG).')
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result as string
      setImagePreview(dataUrl)
      const [meta, b64] = dataUrl.split(',')
      const mediaType = meta.match(/data:(.*?);/)?.[1] || 'image/png'
      extract({ image_base64: b64, media_type: mediaType })
    }
    reader.readAsDataURL(file)
  }

  const onPaste = (e: ClipboardEvent) => {
    const item = Array.from(e.clipboardData.items).find(i => i.type.startsWith('image/'))
    if (item) {
      e.preventDefault()
      onImage(item.getAsFile())
    }
  }

  const confirmImport = async () => {
    if (!rows) return
    const valid = rows.filter(r => r.symbol.trim() && parseFloat(r.shares) > 0)
    if (!valid.length) {
      setErr('Nothing left to import.')
      return
    }
    setBusy(true)
    setErr(null)
    try {
      await api.post(`/portfolio/${slug}/import-holdings`, {
        holdings: valid.map(r => ({
          symbol: r.symbol.trim().toUpperCase(),
          shares: parseFloat(r.shares),
          cost_basis: r.cost_basis ? parseFloat(r.cost_basis) : 0,
        })),
      })
      onDone(valid.length)
    } catch (error: any) {
      setErr(error.response?.data?.detail || "Couldn't save those holdings. Check the numbers.")
      setBusy(false)
    }
  }

  // ── Review step ───────────────────────────────────────────────
  if (rows) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-apple-gray-600">
          Here's what Compass found — <strong>check the numbers</strong>, fix anything that's off, then confirm.
        </p>
        {warnings.length > 0 && (
          <div className="rounded-xl bg-apple-yellow/10 p-2.5 text-xs text-yellow-800">
            {warnings.slice(0, 4).map((w, i) => <p key={i}>{w}</p>)}
          </div>
        )}
        <div className="space-y-1.5">
          <div className="grid grid-cols-[1fr_5rem_6rem_2rem] gap-1.5 px-1 text-[10px] font-semibold uppercase tracking-wide text-apple-gray-400">
            <span>Symbol</span><span>Shares</span><span>Paid/share</span><span />
          </div>
          {rows.map((r, i) => (
            <div key={i} className="grid grid-cols-[1fr_5rem_6rem_2rem] items-center gap-1.5">
              <input value={r.symbol} onChange={e => setRows(rows.map((x, j) => j === i ? { ...x, symbol: e.target.value.toUpperCase() } : x))}
                className={`${inputCls} min-h-[40px] font-medium`} />
              <input value={r.shares} inputMode="decimal" onChange={e => setRows(rows.map((x, j) => j === i ? { ...x, shares: e.target.value } : x))}
                className={`${inputCls} min-h-[40px]`} />
              <input value={r.cost_basis} inputMode="decimal" placeholder="?" onChange={e => setRows(rows.map((x, j) => j === i ? { ...x, cost_basis: e.target.value } : x))}
                className={`${inputCls} min-h-[40px]`} />
              <button onClick={() => setRows(rows.filter((_, j) => j !== i))}
                className="flex min-h-[40px] items-center justify-center text-apple-gray-300 active:text-apple-red">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
        {err && <p className="text-xs text-apple-red">{err}</p>}
        <div className="grid grid-cols-[1fr_2fr] gap-2">
          <button onClick={() => { setRows(null); setErr(null); setImagePreview(null) }}
            className="min-h-[48px] rounded-xl border border-apple-gray-200 text-sm font-medium text-apple-gray-600">
            Start over
          </button>
          <button onClick={confirmImport} disabled={busy} className={primaryBtn}>
            {busy ? 'Saving…' : `Add ${rows.filter(r => r.symbol.trim() && parseFloat(r.shares) > 0).length} holdings`}
          </button>
        </div>
      </div>
    )
  }

  // ── Input step ────────────────────────────────────────────────
  return (
    <div className="space-y-3" onPaste={onPaste}>
      <div className="grid grid-cols-3 gap-1.5">
        {([
          ['photo', Camera, 'Screenshot'],
          ['paste', ClipboardPaste, 'Paste text'],
          ['csv', FileText, 'CSV file'],
        ] as const).map(([m, Icon, label]) => (
          <button key={m} onClick={() => { setMode(m); setErr(null) }}
            className={`flex min-h-[44px] flex-col items-center justify-center gap-0.5 rounded-xl border text-[11px] font-medium ${
              mode === m ? 'border-apple-blue bg-apple-blue/5 text-apple-blue' : 'border-apple-gray-200 bg-white text-apple-gray-500'
            }`}>
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {mode === 'photo' && (
        <div className="space-y-2">
          <p className="text-xs text-apple-gray-500">
            Take a screenshot of your positions in your brokerage app or website, then choose it here
            (or just paste it with {navigator.platform.includes('Mac') ? '⌘V' : 'Ctrl+V'}).
            Compass reads the holdings out of the picture.
          </p>
          <label className="flex min-h-[80px] cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-apple-gray-300 text-sm font-medium text-apple-gray-600 active:bg-apple-gray-50">
            <Upload size={18} />
            {busy ? 'Reading your screenshot…' : 'Choose screenshot'}
            <input type="file" accept="image/*" className="hidden" disabled={busy}
              onChange={e => onImage(e.target.files?.[0])} />
          </label>
          {imagePreview && busy && (
            <img src={imagePreview} alt="" className="max-h-32 w-full rounded-xl border border-apple-gray-200 object-cover opacity-60" />
          )}
        </div>
      )}

      {mode === 'paste' && (
        <div className="space-y-2">
          <p className="text-xs text-apple-gray-500">
            Copy the rows from your brokerage's positions page — messy is fine — and paste them here.
          </p>
          <textarea value={text} onChange={e => setText(e.target.value)} rows={6}
            placeholder={'e.g.\nApple Inc AAPL  25 shares  avg $148.50\nVanguard S&P 500 ETF  12 shares'}
            className="w-full rounded-xl border border-apple-gray-200 bg-apple-gray-50 p-3 text-xs" />
          <button onClick={() => extract({ text })} disabled={busy || !text.trim()} className={primaryBtn}>
            {busy ? 'Reading…' : 'Read my holdings'}
          </button>
        </div>
      )}

      {mode === 'csv' && (
        <div className="space-y-2">
          <p className="text-xs text-apple-gray-500">
            Export positions from your broker as a CSV file (needs Symbol and Shares columns).
          </p>
          <label className="flex min-h-[80px] cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-apple-gray-300 text-sm font-medium text-apple-gray-600 active:bg-apple-gray-50">
            <Upload size={18} />
            {busy ? 'Reading…' : 'Choose CSV file'}
            <input type="file" accept=".csv,text/csv" className="hidden" disabled={busy}
              onChange={e => e.target.files?.[0]?.text().then(t => extract({ text: t }))} />
          </label>
        </div>
      )}

      {busy && mode !== 'photo' && null}
      {err && <p className="text-xs text-apple-red">{err}</p>}
    </div>
  )
}
