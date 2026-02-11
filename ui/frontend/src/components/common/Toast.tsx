import { X, CheckCircle, AlertCircle, Info } from 'lucide-react'
import type { Toast as ToastType } from '../../hooks/useToast'

interface Props {
  toasts: ToastType[]
  onRemove: (id: number) => void
}

const icons = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
}

const colors = {
  success: 'bg-apple-green',
  error: 'bg-apple-red',
  info: 'bg-apple-blue',
}

export default function ToastContainer({ toasts, onRemove }: Props) {
  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-20 inset-x-4 md:bottom-4 md:right-4 md:left-auto z-50 space-y-2">
      {toasts.map(toast => {
        const Icon = icons[toast.type]
        return (
          <div
            key={toast.id}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-white text-sm shadow-lg ${colors[toast.type]} animate-slide-up`}
          >
            <Icon size={18} />
            <span>{toast.message}</span>
            <button onClick={() => onRemove(toast.id)} className="ml-2 opacity-70 hover:opacity-100">
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}
