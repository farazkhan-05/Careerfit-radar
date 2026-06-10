const variants = {
  primary: 'border-ink bg-ink text-white hover:bg-[#0f1722]',
  secondary: 'border-ink/15 bg-white text-ink hover:border-ink hover:bg-paper',
  danger: 'border-coral bg-coral text-white hover:bg-[#e85f55]',
  ghost: 'border-transparent bg-transparent text-muted hover:border-ink/10 hover:bg-white hover:text-ink',
  success: 'border-brand-600 bg-brand-500 text-ink hover:bg-brand-400',
  sun: 'border-ink bg-sun text-ink hover:bg-[#f4bc2d]',
}

const sizes = {
  sm: 'min-h-8 px-3 py-1.5 text-xs',
  md: 'min-h-10 px-4 py-2 text-sm',
  lg: 'min-h-11 px-5 py-2.5 text-sm',
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
        inline-flex items-center justify-center gap-2 rounded-lg border font-bold
        transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-brand-300 focus:ring-offset-2
        disabled:cursor-not-allowed disabled:opacity-50
        enabled:hover:-translate-x-0.5 enabled:hover:-translate-y-0.5 enabled:hover:shadow-button
        enabled:active:translate-x-0 enabled:active:translate-y-0 enabled:active:shadow-none
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
