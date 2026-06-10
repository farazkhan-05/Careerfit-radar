export default function Spinner({ size = 'md', className = '' }) {
  const sizes = { sm: 'h-4 w-4', md: 'h-6 w-6', lg: 'h-9 w-9' }
  return (
    <div
      className={`rounded-full border-2 border-ink/15 border-t-brand-500 animate-spin ${sizes[size]} ${className}`}
    />
  )
}

export function PageSpinner() {
  return (
    <div className="flex items-center justify-center py-20">
      <Spinner size="lg" />
    </div>
  )
}
