import { useQuery } from '@tanstack/react-query'
import { Download, CheckCircle, XCircle, Activity } from 'lucide-react'
import { getLiveness, getReadiness, downloadJobsCsv, downloadApplicationsCsv } from '../api/health'
import { Card, CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { PageSpinner } from '../components/ui/Spinner'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function StatusRow({ label, status, detail }) {
  const ok = status === 'ok' || status === 'configured'
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-slate-100 last:border-0">
      <span className="text-sm font-medium text-slate-600">{label}</span>
      <div className="flex items-center gap-2">
        {detail && <span className="text-xs text-slate-400">{detail}</span>}
        {ok ? (
          <CheckCircle className="h-4 w-4 text-emerald-500" />
        ) : (
          <XCircle className="h-4 w-4 text-rose-400" />
        )}
      </div>
    </div>
  )
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function Settings() {
  const liveQ = useQuery({ queryKey: ['health', 'live'], queryFn: getLiveness, retry: false })
  const readyQ = useQuery({ queryKey: ['health', 'ready'], queryFn: getReadiness, retry: false })

  const apiOnline = !liveQ.isError
  const readiness = readyQ.data?.status ?? (readyQ.isError ? 'unavailable' : 'checking…')
  const checks = readyQ.data?.checks ?? {}

  async function handleExport(fn, filename) {
    try {
      const blob = await fn()
      downloadBlob(blob, filename)
    } catch (err) {
      alert(`Export failed: ${err.message}`)
    }
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">Settings</h1>
        <p className="text-slate-400 mt-1 font-medium">API connection and data exports</p>
      </div>

      <div className="space-y-6">
        {/* API Connection */}
        <Card>
          <CardHeader
            title="API Connection"
            action={
              <div
                className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full ${
                  apiOnline ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-600'
                }`}
              >
                <Activity className="h-3 w-3" />
                {apiOnline ? 'Online' : 'Offline'}
              </div>
            }
          />

          <div className="mb-4">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Endpoint
            </div>
            <code className="text-sm font-mono bg-slate-50 text-slate-600 px-3 py-2 rounded-xl block border border-slate-100">
              {apiUrl}
            </code>
            <p className="text-xs text-slate-400 mt-1.5 font-medium">
              Set <code className="bg-slate-100 px-1 rounded">VITE_API_URL</code> in{' '}
              <code className="bg-slate-100 px-1 rounded">frontend/.env</code> to change this.
            </p>
          </div>

          {readyQ.isLoading ? (
            <PageSpinner />
          ) : (
            <div>
              <StatusRow label="API liveness" status={apiOnline ? 'ok' : 'failed'} />
              <StatusRow label="Overall readiness" status={readiness} detail={readiness} />
              {Object.entries(checks).map(([key, val]) => (
                <StatusRow key={key} label={key.charAt(0).toUpperCase() + key.slice(1)} status={val} detail={val} />
              ))}
            </div>
          )}
        </Card>

        {/* Exports */}
        <Card>
          <CardHeader title="Export Data" subtitle="Download your data as CSV files" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Button
              variant="secondary"
              onClick={() => handleExport(downloadJobsCsv, 'jobs.csv')}
            >
              <Download className="h-4 w-4" />
              Download Jobs CSV
            </Button>
            <Button
              variant="secondary"
              onClick={() => handleExport(downloadApplicationsCsv, 'applications.csv')}
            >
              <Download className="h-4 w-4" />
              Download Applications CSV
            </Button>
          </div>
        </Card>

        {/* About */}
        <Card>
          <CardHeader title="About CareerFit Radar" />
          <div className="text-sm text-slate-500 space-y-1.5">
            <p className="font-medium">
              CareerFit Radar is an AI-powered job intelligence platform. It helps you find, score,
              and track high-fit job opportunities.
            </p>
            <p className="text-slate-400 text-xs pt-1">
              Backend: FastAPI · Database: PostgreSQL + pgvector · AI: Gemini · Workflows: LangGraph
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}
