const fieldClass = `
  w-full rounded-lg border border-ink/15 bg-white px-3.5 py-2.5 text-sm font-medium text-ink
  placeholder:text-muted/60
  focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200
  disabled:cursor-not-allowed disabled:opacity-50
  transition-all duration-150
`

function FieldShell({ label, error, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-xs font-extrabold uppercase tracking-[0.14em] text-muted">{label}</label>
      )}
      {children}
      {error && <p className="text-xs font-bold text-rose-600">{error}</p>}
    </div>
  )
}

export function Input({ label, error, className = '', ...props }) {
  return (
    <FieldShell label={label} error={error}>
      <input
        className={`${fieldClass} ${error ? 'border-coral focus:border-coral focus:ring-coral/20' : ''} ${className}`}
        {...props}
      />
    </FieldShell>
  )
}

export function Select({ label, error, children, className = '', ...props }) {
  return (
    <FieldShell label={label} error={error}>
      <select
        className={`${fieldClass} ${error ? 'border-coral focus:border-coral focus:ring-coral/20' : ''} ${className}`}
        {...props}
      >
        {children}
      </select>
    </FieldShell>
  )
}

export function Textarea({ label, error, className = '', ...props }) {
  return (
    <FieldShell label={label} error={error}>
      <textarea
        className={`${fieldClass} resize-none ${error ? 'border-coral focus:border-coral focus:ring-coral/20' : ''} ${className}`}
        {...props}
      />
    </FieldShell>
  )
}
