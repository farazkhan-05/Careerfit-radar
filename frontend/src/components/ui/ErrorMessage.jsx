import { AlertCircle } from 'lucide-react'

export default function ErrorMessage({ message, className = '' }) {
  if (!message) return null
  return (
    <div
      className={`flex items-start gap-2.5 rounded-lg bg-rose-50 border border-rose-200 px-4 py-3 text-sm text-rose-700 ${className}`}
    >
      <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
      <span>{message}</span>
    </div>
  )
}

export function SuccessMessage({ message, className = '' }) {
  if (!message) return null
  return (
    <div
      className={`flex items-start gap-2.5 rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 ${className}`}
    >
      <span>✓</span>
      <span>{message}</span>
    </div>
  )
}
