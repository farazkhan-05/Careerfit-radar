const variants = {
  primary: 'bg-brand-500 hover:bg-brand-600 text-white',
  secondary: 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-200',
  danger: 'bg-rose-500 hover:bg-rose-600 text-white',
  ghost: 'hover:bg-slate-100 text-slate-600',
  success: 'bg-emerald-500 hover:bg-emerald-600 text-white',
}

const sizes = {
  sm: 'px-4 py-1.5 text-xs',
  md: 'px-5 py-2 text-sm',
  lg: 'px-6 py-2.5 text-sm',
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  className = '',
  ...props
}) {
  return (
    <button
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center gap-2 rounded-full font-semibold
        transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed
        hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:shadow-none
        ${variants[variant]}
        ${sizes[size]}
        ${className}
      `}
      {...props}
    >
      {loading && (
        <span className="h-3.5 w-3.5 rounded-full border-2 border-current border-t-transparent animate-spin" />
      )}
      {children}
    </button>
  )
}
