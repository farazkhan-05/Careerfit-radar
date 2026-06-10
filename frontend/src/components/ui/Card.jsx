export function Card({ children, className = '', padding = true, accent = 'var(--mint)' }) {
  return (
    <div
      className={`play-card soft-pop ${padding ? 'p-5' : ''} ${className}`}
      style={{ '--card-accent': accent }}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action, eyebrow }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && (
          <div className="mb-1 text-[10px] font-extrabold uppercase tracking-[0.2em] text-muted">
            {eyebrow}
          </div>
        )}
        <h3 className="font-display text-lg font-bold leading-tight text-ink">{title}</h3>
        {subtitle && <p className="mt-1 text-sm font-medium leading-5 text-muted">{subtitle}</p>}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  )
}
