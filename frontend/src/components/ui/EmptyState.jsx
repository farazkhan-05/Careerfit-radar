import { SearchX } from 'lucide-react'

export default function EmptyState({ icon, title, description, action }) {
  const Icon = typeof icon === 'function' ? icon : SearchX

  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-ink/15 bg-white/70 px-6 py-14 text-center">
      <div className="mb-4 grid h-14 w-14 place-items-center rounded-lg border border-ink/10 bg-sun/25 text-ink shadow-[4px_4px_0_rgba(24,33,47,0.08)]">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="font-display text-lg font-bold text-ink">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-sm font-medium leading-6 text-muted">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
