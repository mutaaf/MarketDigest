interface Props {
  status: 'green' | 'yellow' | 'red' | 'gray'
  size?: 'sm' | 'md'
}

const colors = {
  green: 'bg-apple-green',
  yellow: 'bg-apple-yellow',
  red: 'bg-apple-red',
  gray: 'bg-apple-gray-300',
}

export default function StatusDot({ status, size = 'sm' }: Props) {
  const sizeClass = size === 'sm' ? 'w-2 h-2' : 'w-3 h-3'
  return (
    <span className={`inline-block ${sizeClass} rounded-full ${colors[status]}`} />
  )
}
