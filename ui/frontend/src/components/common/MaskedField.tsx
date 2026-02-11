import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

interface Props {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  onSave?: () => void
}

export default function MaskedField({ value, onChange, placeholder, onSave }: Props) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex-1">
        <input
          type={visible ? 'text' : 'password'}
          className="input-field pr-10"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
        />
        <button
          onClick={() => setVisible(!visible)}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-apple-gray-400 hover:text-apple-gray-600"
          type="button"
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {onSave && (
        <button onClick={onSave} className="btn-primary text-xs">
          Save
        </button>
      )}
    </div>
  )
}
