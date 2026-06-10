import { useQuery } from '@tanstack/react-query'
import { Activity, CheckCircle2, Download, Info, Server, XCircle } from 'lucide-react'
import { getLiveness, getReadiness, downloadJobsCsv, downloadApplicationsCsv } from '../api/health'
import { Card, CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { PageSpinner } from '../components/ui/Spinner'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function StatusRow({ label, status, detail }) {
  const ok = status === 'ok' || status === 'configured'
  return (
    <div className="grid gap-2 border-b border-ink/10 py-3 last:border-0 sm:grid-cols-[1fr_auto] sm:items-center">
      <span className="text-sm font-bold text-ink">{label}</span>
      <div className="flex items-center gap-2 sm:justify-end">
        {detail && <span className="text-xs font-bold text-muted">{detail}</span>}
        {ok ? (
          <CheckCircle2 className="h-4 w-4 text-brand-600" />
        ) : (
          <XCircle className="h-4 w-4 text-rose-600" />
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
  const readiness = readyQ.data?.status ?? (readyQ.isError ? 'unavailable' : 'checking...')
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
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="mb-6">
        <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-muted">System</p>
        <h1 className="mt-1 font-display text-4xl font-bold leading-tight text-ink">Settings</h1>
        <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-muted">
          Connection status, exports, and local runtime details.
        </p>
      </header>

      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <Card accent="var(--mint)">
          <CardHeader
            title="API connection"
            subtitle="Backend health and readiness checks"
            eyebrow="Status"
            action={
              <div
                className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1 text-xs font-extrabold ${
                  apiOnline ? 'border-brand-500/25 bg-brand-100 text-brand-800' : 'border-coral/25 bg-coral/10 text-rose-700'
                }`}
              >
                <Activity className="h-3.5 w-3.5" />
                {apiOnline ? 'Online' : 'Offline'}
              </div>
            }
          />

          <div className="mb-5 rounded-lg border border-ink/10 bg-white p-4">
            <div className="mb-2 flex items-center gap-2 text-xs font-extrabold uppercase tracking-[0.16em] text-muted">
              <Server className="h-4 w-4" />
              Endpoint
            </div>
            <code className="ink-surface block overflow-x-auto rounded-lg px-3 py-2 font-mono text-sm font-semibold">
              {apiUrl}
            </code>
            <p className="mt-2 text-xs font-medium leading-5 text-muted">
              Set <code className="rounded bg-slate-100 px-1 font-semibold text-ink">VITE_API_URL</code> in{' '}
              <code className="rounded bg-slate-100 px-1 font-semibold text-ink">frontend/.env</code> to change this.
            </p>
          </div>

          {readyQ.isLoading ? (
            <PageSpinner />
          ) : (
            <div className="rounded-lg border border-ink/10 bg-white px-4">
              <StatusRow label="API liveness" status={apiOnline ? 'ok' : 'failed'} />
              <StatusRow label="Overall readiness" status={readiness} detail={readiness} />
              {Object.entries(checks).map(([key, val]) => (
                <StatusRow key={key} label={key.charAt(0).toUpperCase() + key.slice(1)} status={val} detail={val} />
              ))}
            </div>
          )}
        </Card>

        <div className="space-y-5">
          <Card accent="var(--sun)">
            <CardHeader title="Export data" subtitle="Download CSV files" eyebrow="Portability" />
            <div className="grid gap-3">
              <Button
                variant="secondary"
                onClick={() => handleExport(downloadJobsCsv, 'jobs.csv')}
                className="justify-start"
              >
                <Download className="h-4 w-4" />
                Jobs CSV
              </Button>
              <Button
                variant="secondary"
                onClick={() => handleExport(downloadApplicationsCsv, 'applications.csv')}
                className="justify-start"
              >
                <Download className="h-4 w-4" />
                Applications CSV
              </Button>
            </div>
          </Card>

          <Card accent="var(--sky)">
            <CardHeader
              title="About"
              eyebrow="Build"
              action={
                <div className="grid h-9 w-9 place-items-center rounded-lg bg-sky/20 text-blue-700">
                  <Info className="h-5 w-5" />
                </div>
              }
            />
            <div className="space-y-3 text-sm font-medium leading-6 text-muted">
              <p>
                CareerFit Radar helps you find, score, and track high-fit job opportunities in one focused workspace.
              </p>
              <p className="rounded-lg border border-ink/10 bg-white p-3 text-xs font-bold text-muted">
                Backend: FastAPI - Database: PostgreSQL + pgvector - AI: Gemini - Workflows: LangGraph
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
