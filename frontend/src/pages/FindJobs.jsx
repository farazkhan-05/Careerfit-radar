import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Plus, ChevronDown, ChevronUp, Zap } from 'lucide-react'
import { importGreenhouse, importLever, importRemotive, importArbeitnow, listSourceRuns } from '../api/sources'
import { triggerWorkflow } from '../api/workflows'
import { createManualJob } from '../api/jobs'
import { Card, CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Input, Select, Textarea } from '../components/ui/Input'
import ErrorMessage, { SuccessMessage } from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'
import Badge from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'

const SOURCE_COLORS = {
  greenhouse: 'green',
  lever: 'blue',
  remotive: 'teal',
  arbeitnow: 'orange',
}

function SourceCard({ name, emoji, description, params, onImport, loading }) {
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <div className="text-2xl">{emoji}</div>
        <div>
          <div className="text-sm font-semibold text-slate-800 capitalize">{name}</div>
          <div className="text-xs text-slate-500">{description}</div>
        </div>
      </div>
      {params}
      <Button onClick={onImport} loading={loading} size="sm" className="w-full mt-auto">
        Import from {name.charAt(0).toUpperCase() + name.slice(1)}
      </Button>
    </Card>
  )
}

function RunsTable({ runs }) {
  if (runs.length === 0) {
    return (
      <EmptyState
        icon="📋"
        title="No imports yet"
        description="Import jobs from a source above to see activity here."
      />
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
                <Badge color={SOURCE_COLORS[run.source_name] ?? 'gray'}>
                  {run.source_name}
                </Badge>
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

  const [greenhouseToken, setGreenhouseToken] = useState('')
  const [leverSlug, setLeverSlug] = useState('')
  const [remotiveSearch, setRemotiveSearch] = useState('')
  const [showManual, setShowManual] = useState(false)
  const [manualForm, setManualForm] = useState({
    company_name: '',
    title: '',
    apply_url: '',
    location: '',
    remote_type: '',
    description: '',
  })

  const [importStatus, setImportStatus] = useState(null)
  const [workflowStatus, setWorkflowStatus] = useState(null)
  const [manualStatus, setManualStatus] = useState(null)

  const runsQ = useQuery({
    queryKey: ['sourceRuns'],
    queryFn: () => listSourceRuns({ limit: 15 }),
  })

  function onImportSuccess(data, sourceName) {
    queryClient.invalidateQueries({ queryKey: ['sourceRuns'] })
    queryClient.invalidateQueries({ queryKey: ['jobs'] })
    setImportStatus({
      type: 'success',
      message: `${sourceName}: imported ${data.jobs_stored} new job${data.jobs_stored !== 1 ? 's' : ''} (${data.jobs_fetched} fetched).`,
    })
  }

  function onImportError(err) {
    setImportStatus({ type: 'error', message: err.message })
  }

  const greenhouseMut = useMutation({
    mutationFn: () => importGreenhouse(greenhouseToken),
    onSuccess: (data) => onImportSuccess(data, 'Greenhouse'),
    onError: onImportError,
  })

  const leverMut = useMutation({
    mutationFn: () => importLever(leverSlug),
    onSuccess: (data) => onImportSuccess(data, 'Lever'),
    onError: onImportError,
  })

  const remotiveMut = useMutation({
    mutationFn: () => importRemotive(remotiveSearch),
    onSuccess: (data) => onImportSuccess(data, 'Remotive'),
    onError: onImportError,
  })

  const arbeitnowMut = useMutation({
    mutationFn: importArbeitnow,
    onSuccess: (data) => onImportSuccess(data, 'Arbeitnow'),
    onError: onImportError,
  })

  const workflowMut = useMutation({
    mutationFn: triggerWorkflow,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
      setWorkflowStatus({ type: 'success', message: `AI matching run started (${data.run_id}).` })
    },
    onError: (err) => setWorkflowStatus({ type: 'error', message: err.message }),
  })

  const manualMut = useMutation({
    mutationFn: () =>
      createManualJob({
        ...manualForm,
        source: 'manual',
        source_job_id: `manual-${manualForm.company_name}-${manualForm.title}-${Date.now()}`,
        remote_type: manualForm.remote_type || null,
        location: manualForm.location || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setManualStatus({ type: 'success', message: 'Job added.' })
      setManualForm({ company_name: '', title: '', apply_url: '', location: '', remote_type: '', description: '' })
    },
    onError: (err) => setManualStatus({ type: 'error', message: err.message }),
  })

  const runs = runsQ.data?.items ?? []

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Find Jobs</h1>
        <p className="text-slate-500 mt-1">Import fresh listings from job sources or add one manually</p>
      </div>

      {/* Import feedback */}
      {importStatus?.type === 'success' && (
        <SuccessMessage message={importStatus.message} className="mb-5" />
      )}
      {importStatus?.type === 'error' && (
        <ErrorMessage message={importStatus.message} className="mb-5" />
      )}

      {/* Source cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <SourceCard
          name="greenhouse"
          emoji="🌱"
          description="ATS job board"
          loading={greenhouseMut.isPending}
          onImport={() => { setImportStatus(null); greenhouseMut.mutate() }}
          params={
            <Input
              placeholder="Board token (e.g. stripe)"
              value={greenhouseToken}
              onChange={(e) => setGreenhouseToken(e.target.value)}
            />
          }
        />
        <SourceCard
          name="lever"
          emoji="⚙️"
          description="ATS job board"
          loading={leverMut.isPending}
          onImport={() => { setImportStatus(null); leverMut.mutate() }}
          params={
            <Input
              placeholder="Company slug (e.g. netflix)"
              value={leverSlug}
              onChange={(e) => setLeverSlug(e.target.value)}
            />
          }
        />
        <SourceCard
          name="remotive"
          emoji="🌍"
          description="Remote job board"
          loading={remotiveMut.isPending}
          onImport={() => { setImportStatus(null); remotiveMut.mutate() }}
          params={
            <Input
              placeholder="Keyword (e.g. python)"
              value={remotiveSearch}
              onChange={(e) => setRemotiveSearch(e.target.value)}
            />
          }
        />
        <SourceCard
          name="arbeitnow"
          emoji="🤝"
          description="Global job board"
          loading={arbeitnowMut.isPending}
          onImport={() => { setImportStatus(null); arbeitnowMut.mutate() }}
          params={<div className="text-xs text-slate-400 italic">No configuration needed</div>}
        />
      </div>

      {/* AI Matching */}
      <Card className="mb-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Zap className="h-4 w-4 text-amber-500" />
              <span className="text-sm font-semibold text-slate-900">Run AI Matching</span>
            </div>
            <p className="text-sm text-slate-500">
              Score and rank all imported jobs against your resume with Gemini AI.
            </p>
          </div>
          <Button
            onClick={() => { setWorkflowStatus(null); workflowMut.mutate() }}
            loading={workflowMut.isPending}
            className="flex-shrink-0"
          >
            <RefreshCw className="h-4 w-4" />
            Run Matching
          </Button>
        </div>
        {workflowStatus?.type === 'success' && (
          <SuccessMessage message={workflowStatus.message} className="mt-3" />
        )}
        {workflowStatus?.type === 'error' && (
          <ErrorMessage message={workflowStatus.message} className="mt-3" />
        )}
      </Card>

      {/* Manual job */}
      <Card className="mb-6">
        <button
          className="flex items-center justify-between w-full text-left"
          onClick={() => setShowManual((v) => !v)}
        >
          <div className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-brand-600" />
            <span className="text-sm font-semibold text-slate-900">Add a job manually</span>
          </div>
          {showManual ? (
            <ChevronUp className="h-4 w-4 text-slate-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-400" />
          )}
        </button>
        {showManual && (
          <div className="mt-5 space-y-4">
            {manualStatus?.type === 'success' && (
              <SuccessMessage message={manualStatus.message} />
            )}
            {manualStatus?.type === 'error' && (
              <ErrorMessage message={manualStatus.message} />
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Company"
                placeholder="Acme Corp"
                value={manualForm.company_name}
                onChange={(e) => setManualForm((f) => ({ ...f, company_name: e.target.value }))}
              />
              <Input
                label="Job Title"
                placeholder="Software Engineer"
                value={manualForm.title}
                onChange={(e) => setManualForm((f) => ({ ...f, title: e.target.value }))}
              />
              <Input
                label="Apply Link"
                placeholder="https://company.com/jobs/123"
                value={manualForm.apply_url}
                onChange={(e) => setManualForm((f) => ({ ...f, apply_url: e.target.value }))}
              />
              <Input
                label="Location"
                placeholder="Berlin, Germany"
                value={manualForm.location}
                onChange={(e) => setManualForm((f) => ({ ...f, location: e.target.value }))}
              />
              <Select
                label="Work Mode"
                value={manualForm.remote_type}
                onChange={(e) => setManualForm((f) => ({ ...f, remote_type: e.target.value }))}
              >
                <option value="">Not specified</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">On-site</option>
              </Select>
            </div>
            <Textarea
              label="Job Description"
              placeholder="Paste the job description here…"
              rows={5}
              value={manualForm.description}
              onChange={(e) => setManualForm((f) => ({ ...f, description: e.target.value }))}
            />
            <div className="flex justify-end">
              <Button
                onClick={() => { setManualStatus(null); manualMut.mutate() }}
                loading={manualMut.isPending}
                disabled={!manualForm.company_name || !manualForm.title || !manualForm.apply_url || !manualForm.description}
              >
                Add Job
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Recent imports */}
      <Card>
        <CardHeader title="Recent Imports" subtitle="Last 15 source runs" />
        {runsQ.isLoading ? <PageSpinner /> : <RunsTable runs={runs} />}
      </Card>
    </div>
  )
}
