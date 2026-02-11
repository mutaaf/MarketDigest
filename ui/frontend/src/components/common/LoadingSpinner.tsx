interface Props {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export default function LoadingSpinner({ size = 'md', className = '' }: Props) {
  const sizeClass = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-10 h-10' }[size]
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className={`${sizeClass} border-2 border-apple-gray-200 border-t-apple-blue rounded-full animate-spin`} />
    </div>
  )
}
