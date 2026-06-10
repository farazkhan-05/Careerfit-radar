export function Card({ children, className = '', padding = true }) {
  return (
    <div
      className={`bg-white rounded-2xl border border-slate-100/80 ${padding ? 'p-5' : ''} ${className}`}
      style={{ boxShadow: '0 10px 30px -10px rgba(99, 102, 241, 0.12)' }}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div>
        <h3 className="text-base font-semibold text-slate-800">{title}</h3>
        {subtitle && <p className="text-sm text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
      {action && <div className="ml-4 flex-shrink-0">{action}</div>}
    </div>
  )
}
