import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, ChevronUp, Plus, Sparkles, Zap } from 'lucide-react'
import { importGreenhouse, importLever, importRemotive, importArbeitnow, listSourceRuns } from '../api/sources'
import { createManualJob } from '../api/jobs'
import { scoreJobs } from '../api/profiles'
import { listProfiles } from '../api/profiles'
import { Card, CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Input, Select, Textarea } from '../components/ui/Input'
import ErrorMessage, { SuccessMessage } from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'
import Badge from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'

const SOURCE_COLORS = { greenhouse: 'green', lever: 'blue', remotive: 'teal', arbeitnow: 'orange' }

function RunsTable({ runs }) {
  if (runs.length === 0) {
    return (
      <EmptyState icon="📋" title="No imports yet" description="Import jobs from a source above to get started." />
    )
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100">
            <th className="text-left py-2 px-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Source</th>
            <th className="text-left py-2 px-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Status</th>
            <th className="text-right py-2 px-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Fetched</th>
            <th className="text-right py-2 px-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Stored</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} className="border-b border-slate-50 hover:bg-slate-50">
              <td className="py-2.5 px-3">
                <Badge color={SOURCE_COLORS[run.source_name] ?? 'gray'}>{run.source_name}</Badge>
              </td>
              <td className="py-2.5 px-3">
                <span className={`text-xs font-medium ${run.status === 'success' ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {run.status}
                </span>
              </td>
              <td className="py-2.5 px-3 text-right text-slate-600">{run.jobs_fetched}</td>
              <td className="py-2.5 px-3 text-right font-medium text-slate-900">{run.jobs_stored}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function FindJobs() {
  const queryClient = useQueryClient()

  const [remotiveSearch, setRemotiveSearch] = useState('')
  const [showAts, setShowAts] = useState(false)
  const [greenhouseToken, setGreenhouseToken] = useState('')
  const [leverSlug, setLeverSlug] = useState('')
  const [showManual, setShowManual] = useState(false)
  const [manualForm, setManualForm] = useState({ company_name: '', title: '', apply_url: '', location: '', remote_type: '', description: '' })

  const [importMsg, setImportMsg] = useState(null)
  const [scoreMsg, setScoreMsg] = useState(null)
  const [manualMsg, setManualMsg] = useState(null)

  const runsQ = useQuery({ queryKey: ['sourceRuns'], queryFn: () => listSourceRuns({ limit: 20 }) })
  const profilesQ = useQuery({ queryKey: ['profiles'], queryFn: () => listProfiles(1, 0) })
  const profile = profilesQ.data?.items?.[0]

  // Auto-suggest keyword from profile
  const suggestedKeyword = profile?.target_roles?.[0] ?? ''

  function onImportSuccess(data, name) {
    queryClient.invalidateQueries({ queryKey: ['sourceRuns'] })
    queryClient.invalidateQueries({ queryKey: ['jobs'] })
    setImportMsg({ type: 'success', message: `${name}: ${data.jobs_stored} new job${data.jobs_stored !== 1 ? 's' : ''} added (${data.jobs_fetched} fetched).` })
  }
  function onImportError(err) { setImportMsg({ type: 'error', message: err.message }) }

  const remotiveMut = useMutation({
    mutationFn: () => importRemotive(remotiveSearch || suggestedKeyword || undefined),
    onSuccess: (d) => onImportSuccess(d, 'Remotive'),
    onError: onImportError,
  })

  const arbeitnowMut = useMutation({
    mutationFn: importArbeitnow,
    onSuccess: (d) => onImportSuccess(d, 'Arbeitnow'),
    onError: onImportError,
  })

  const greenhouseMut = useMutation({
    mutationFn: () => importGreenhouse(greenhouseToken),
    onSuccess: (d) => onImportSuccess(d, 'Greenhouse'),
    onError: onImportError,
  })

  const leverMut = useMutation({
    mutationFn: () => importLever(leverSlug),
    onSuccess: (d) => onImportSuccess(d, 'Lever'),
    onError: onImportError,
  })

  const scoreMut = useMutation({
    mutationFn: scoreJobs,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      if (data.scored === 0) {
        setScoreMsg({ type: 'success', message: `All ${data.total_scored} jobs already scored. Go to Job Matches to see results.` })
      } else {
        setScoreMsg({ type: 'success', message: `Scored ${data.scored} jobs against your profile. Go to Job Matches to see results sorted by fit.` })
      }
    },
    onError: (err) => setScoreMsg({ type: 'error', message: err.message }),
  })

  const manualMut = useMutation({
    mutationFn: () => createManualJob({ ...manualForm, source: 'manual', source_job_id: `manual-${Date.now()}`, remote_type: manualForm.remote_type || null, location: manualForm.location || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setManualMsg({ type: 'success', message: 'Job added.' })
      setManualForm({ company_name: '', title: '', apply_url: '', location: '', remote_type: '', description: '' })
    },
    onError: (err) => setManualMsg({ type: 'error', message: err.message }),
  })

  const runs = runsQ.data?.items ?? []
  const anyImporting = remotiveMut.isPending || arbeitnowMut.isPending

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Find Jobs</h1>
        <p className="text-slate-500 mt-1">Import jobs, then score them against your resume with AI</p>
      </div>

      {/* Step 1 — Import */}
      <div className="flex items-center gap-3 mb-4">
        <div className="h-7 w-7 rounded-full bg-brand-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">1</div>
        <h2 className="text-base font-semibold text-slate-800">Import jobs</h2>
      </div>

      {importMsg?.type === 'success' && <SuccessMessage message={importMsg.message} className="mb-4" />}
      {importMsg?.type === 'error' && <ErrorMessage message={importMsg.message} className="mb-4" />}

      <div className="space-y-3 mb-6">
        {/* Remotive */}
        <Card>
          <div className="flex items-center gap-3 mb-3">
            <span className="text-xl">🌍</span>
            <div>
              <div className="text-sm font-semibold text-slate-800">Remotive <span className="text-xs font-normal text-emerald-600 ml-1">General job board</span></div>
              <div className="text-xs text-slate-500">Remote jobs across all industries and roles</div>
            </div>
          </div>
          <div className="flex gap-2">
            <Input
              placeholder={suggestedKeyword ? `e.g. "${suggestedKeyword}" (from your profile)` : 'Keyword — e.g. "python" or "product manager"'}
              value={remotiveSearch}
              onChange={(e) => setRemotiveSearch(e.target.value)}
              className="flex-1"
            />
            <Button
              loading={remotiveMut.isPending}
              onClick={() => { setImportMsg(null); remotiveMut.mutate() }}
              disabled={anyImporting && !remotiveMut.isPending}
            >
              Import
            </Button>
          </div>
        </Card>

        {/* Arbeitnow */}
        <Card>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="text-xl">🤝</span>
              <div>
                <div className="text-sm font-semibold text-slate-800">Arbeitnow <span className="text-xs font-normal text-emerald-600 ml-1">General job board</span></div>
                <div className="text-xs text-slate-500">International jobs — no keyword needed</div>
              </div>
            </div>
            <Button
              loading={arbeitnowMut.isPending}
              onClick={() => { setImportMsg(null); arbeitnowMut.mutate() }}
              disabled={anyImporting && !arbeitnowMut.isPending}
            >
              Import
            </Button>
          </div>
        </Card>

        {/* ATS boards — collapsed by default */}
        <div className="border border-slate-200 rounded-xl overflow-hidden">
          <button
            onClick={() => setShowAts(v => !v)}
            className="w-full flex items-center justify-between px-4 py-3 text-left bg-slate-50 hover:bg-slate-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-slate-700">Company ATS boards</span>
              <span className="text-xs text-slate-400 bg-white border border-slate-200 rounded px-1.5 py-0.5">Greenhouse · Lever</span>
              <span className="text-xs text-amber-600">Needs company token</span>
            </div>
            {showAts ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
          </button>

          {showAts && (
            <div className="p-4 space-y-4 border-t border-slate-200">
              <p className="text-xs text-slate-500">These boards are company-specific. You need to know the company's ATS token (e.g. Stripe uses "stripe" on Greenhouse). Find it in the company's careers page URL.</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span>🌱</span>
                    <span className="text-sm font-medium text-slate-700">Greenhouse</span>
                  </div>
                  <div className="flex gap-2">
                    <Input placeholder="Board token (e.g. stripe)" value={greenhouseToken} onChange={(e) => setGreenhouseToken(e.target.value)} />
                    <Button size="sm" loading={greenhouseMut.isPending} onClick={() => { setImportMsg(null); greenhouseMut.mutate() }} disabled={!greenhouseToken}>Go</Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span>⚙️</span>
                    <span className="text-sm font-medium text-slate-700">Lever</span>
                  </div>
                  <div className="flex gap-2">
                    <Input placeholder="Company slug (e.g. netflix)" value={leverSlug} onChange={(e) => setLeverSlug(e.target.value)} />
                    <Button size="sm" loading={leverMut.isPending} onClick={() => { setImportMsg(null); leverMut.mutate() }} disabled={!leverSlug}>Go</Button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Step 2 — Score */}
      <div className="flex items-center gap-3 mb-4">
        <div className="h-7 w-7 rounded-full bg-brand-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">2</div>
        <h2 className="text-base font-semibold text-slate-800">Score jobs against your profile</h2>
      </div>

      <Card className="mb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Zap className="h-4 w-4 text-amber-500" />
              <span className="text-sm font-semibold text-slate-900">AI Match Scoring</span>
              {!profile && (
                <span className="text-xs text-rose-500 bg-rose-50 px-2 py-0.5 rounded-full">Upload resume first</span>
              )}
            </div>
            <p className="text-sm text-slate-500">
              Scores every imported job against your skills, experience, and target roles. Results appear sorted by fit in Job Matches.
            </p>
          </div>
          <Button
            onClick={() => { setScoreMsg(null); scoreMut.mutate() }}
            loading={scoreMut.isPending}
            disabled={!profile}
            className="flex-shrink-0"
          >
            <Sparkles className="h-4 w-4" />
            Score Jobs
          </Button>
        </div>
        {scoreMsg?.type === 'success' && <SuccessMessage message={scoreMsg.message} className="mt-3" />}
        {scoreMsg?.type === 'error' && <ErrorMessage message={scoreMsg.message} className="mt-3" />}
      </Card>

      {/* Step 3 — Manual */}
      <div className="flex items-center gap-3 mb-4">
        <div className="h-7 w-7 rounded-full bg-slate-300 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">3</div>
        <h2 className="text-base font-semibold text-slate-800">Add a job manually <span className="text-xs font-normal text-slate-400">(optional)</span></h2>
      </div>

      <Card className="mb-6">
        <button className="flex items-center justify-between w-full text-left" onClick={() => setShowManual(v => !v)}>
          <div className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-brand-600" />
            <span className="text-sm font-medium text-slate-700">Add a job you found elsewhere</span>
          </div>
          {showManual ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
        </button>
        {showManual && (
          <div className="mt-4 space-y-4">
            {manualMsg?.type === 'success' && <SuccessMessage message={manualMsg.message} />}
            {manualMsg?.type === 'error' && <ErrorMessage message={manualMsg.message} />}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input label="Company" placeholder="Acme Corp" value={manualForm.company_name} onChange={(e) => setManualForm(f => ({ ...f, company_name: e.target.value }))} />
              <Input label="Job Title" placeholder="Software Engineer" value={manualForm.title} onChange={(e) => setManualForm(f => ({ ...f, title: e.target.value }))} />
              <Input label="Apply Link" placeholder="https://..." value={manualForm.apply_url} onChange={(e) => setManualForm(f => ({ ...f, apply_url: e.target.value }))} />
              <Select label="Work Mode" value={manualForm.remote_type} onChange={(e) => setManualForm(f => ({ ...f, remote_type: e.target.value }))}>
                <option value="">Not specified</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">On-site</option>
              </Select>
            </div>
            <Textarea label="Job Description" placeholder="Paste the job description here…" rows={4} value={manualForm.description} onChange={(e) => setManualForm(f => ({ ...f, description: e.target.value }))} />
            <div className="flex justify-end">
              <Button onClick={() => { setManualMsg(null); manualMut.mutate() }} loading={manualMut.isPending} disabled={!manualForm.company_name || !manualForm.title || !manualForm.apply_url || !manualForm.description}>
                Add Job
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Import history */}
      <Card>
        <CardHeader title="Import History" subtitle="Last 20 source runs" />
        {runsQ.isLoading ? <PageSpinner /> : <RunsTable runs={runs} />}
      </Card>
    </div>
  )
}
