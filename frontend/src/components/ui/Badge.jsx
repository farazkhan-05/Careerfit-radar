const colors = {
  gray: 'bg-slate-100 text-slate-600',
  violet: 'bg-brand-100 text-brand-700',
  green: 'bg-emerald-100 text-emerald-700',
  teal: 'bg-teal-100 text-teal-700',
  amber: 'bg-amber-100 text-amber-700',
  orange: 'bg-orange-100 text-orange-700',
  rose: 'bg-rose-100 text-rose-700',
  blue: 'bg-blue-100 text-blue-700',
}

export default function Badge({ children, color = 'gray', className = '' }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors[color]} ${className}`}
    >
      {children}
    </span>
  )
}

export function StatusBadge({ status }) {
  const map = {
    new: { label: 'New', color: 'blue' },
    saved: { label: 'Saved', color: 'violet' },
    duplicate: { label: 'Duplicate', color: 'gray' },
    rejected: { label: 'Rejected', color: 'rose' },
    applied: { label: 'Applied', color: 'teal' },
    interview: { label: 'Interview', color: 'amber' },
    offer: { label: 'Offer', color: 'green' },
    follow_up: { label: 'Follow Up', color: 'orange' },
  }
  const cfg = map[status] ?? { label: status, color: 'gray' }
  return <Badge color={cfg.color}>{cfg.label}</Badge>
}

export function SourceBadge({ source }) {
  const sourceColors = {
    greenhouse: 'green',
    lever: 'blue',
    remotive: 'teal',
    arbeitnow: 'orange',
    manual: 'gray',
    smartrecruiters: 'violet',
  }
  const color = sourceColors[source?.toLowerCase()] ?? 'gray'
  const label = source ? source.charAt(0).toUpperCase() + source.slice(1) : 'Unknown'
  return <Badge color={color}>{label}</Badge>
}
