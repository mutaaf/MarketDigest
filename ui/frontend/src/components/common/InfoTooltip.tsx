import { useState, useRef, useEffect } from 'react'
import { Info } from 'lucide-react'

interface InfoTooltipProps {
  text: string
  forceOpen?: boolean
}

export default function InfoTooltip({ text, forceOpen = false }: InfoTooltipProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const isOpen = forceOpen || open

  useEffect(() => {
    if (!forceOpen) {
      const handleClick = (e: MouseEvent) => {
        if (ref.current && !ref.current.contains(e.target as Node)) {
          setOpen(false)
        }
      }
      document.addEventListener('mousedown', handleClick)
      return () => document.removeEventListener('mousedown', handleClick)
    }
  }, [forceOpen])

  return (
    <div className="relative inline-block" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-apple-gray-100 hover:bg-apple-gray-200 transition-colors"
        aria-label="More info"
      >
        <Info size={12} className="text-apple-gray-500" />
      </button>
      {isOpen && (
        <div className="absolute z-50 left-0 top-7 w-72 p-3 bg-white border border-apple-gray-200 rounded-xl shadow-lg text-xs text-apple-gray-600 leading-relaxed">
          {text}
        </div>
      )}
    </div>
  )
}
