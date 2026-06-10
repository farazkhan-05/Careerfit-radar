import { AlertCircle, CheckCircle2 } from 'lucide-react'

export default function ErrorMessage({ message, className = '' }) {
  if (!message) return null
  return (
    <div
      className={`flex items-start gap-2.5 rounded-lg border border-coral/25 bg-coral/10 px-4 py-3 text-sm font-semibold text-rose-700 ${className}`}
    >
      <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
      <span>{message}</span>
    </div>
  )
}

export function SuccessMessage({ message, className = '' }) {
  if (!message) return null
  return (
    <div
      className={`flex items-start gap-2.5 rounded-lg border border-brand-500/25 bg-brand-100 px-4 py-3 text-sm font-semibold text-brand-800 ${className}`}
    >
      <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0" />
      <span>{message}</span>
    </div>
  )
}
