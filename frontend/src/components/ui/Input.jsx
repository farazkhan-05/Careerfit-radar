export function Input({ label, error, className = '', ...props }) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-semibold text-slate-600">{label}</label>
      )}
      <input
        className={`
          w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-800
          placeholder:text-slate-400
          focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-all duration-150
          ${error ? 'border-rose-400 focus:ring-rose-300' : ''}
          ${className}
        `}
        {...props}
      />
      {error && <p className="text-xs text-rose-500">{error}</p>}
    </div>
  )
}

export function Select({ label, error, children, className = '', ...props }) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-semibold text-slate-600">{label}</label>
      )}
      <select
        className={`
          w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-800
          focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-all duration-150
          ${error ? 'border-rose-400' : ''}
          ${className}
        `}
        {...props}
      >
        {children}
      </select>
      {error && <p className="text-xs text-rose-500">{error}</p>}
    </div>
  )
}

export function Textarea({ label, error, className = '', ...props }) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-semibold text-slate-600">{label}</label>
      )}
      <textarea
        className={`
          w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-800
          placeholder:text-slate-400 resize-none
          focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-all duration-150
          ${error ? 'border-rose-400' : ''}
          ${className}
        `}
        {...props}
      />
      {error && <p className="text-xs text-rose-500">{error}</p>}
    </div>
  )
}
