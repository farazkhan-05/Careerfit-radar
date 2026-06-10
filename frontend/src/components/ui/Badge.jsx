const colors = {
  gray: 'border-slate-200 bg-slate-100 text-slate-700',
  violet: 'border-plum/20 bg-plum/10 text-violet-700',
  green: 'border-brand-500/25 bg-brand-100 text-brand-800',
  teal: 'border-brand-500/25 bg-brand-100 text-brand-800',
  amber: 'border-sun/40 bg-sun/20 text-amber-800',
  orange: 'border-orange-300 bg-orange-100 text-orange-700',
  rose: 'border-coral/30 bg-coral/10 text-rose-700',
  blue: 'border-sky/30 bg-sky/15 text-blue-700',
  ink: 'border-ink bg-ink text-white',
}

function humanize(value) {
  if (!value) return 'Unknown'
  return String(value)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export default function Badge({ children, color = 'gray', className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-bold leading-5 ${colors[color] ?? colors.gray} ${className}`}
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
    ignored: { label: 'Ignored', color: 'gray' },
  }
  const cfg = map[status] ?? { label: humanize(status), color: 'gray' }
  return <Badge color={cfg.color}>{cfg.label}</Badge>
}

export function SourceBadge({ source }) {
  const sourceColors = {
    google_search: 'teal',
    manual: 'gray',
    smartrecruiters: 'violet',
  }
  const color = sourceColors[source?.toLowerCase()] ?? 'gray'
  return <Badge color={color}>{humanize(source)}</Badge>
}
