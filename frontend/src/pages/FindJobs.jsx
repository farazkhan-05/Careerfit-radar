import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ChevronDown,
  ChevronUp,
  Clock3,
  History,
  ListChecks,
  Plus,
  Search,
  Sparkles,
  Zap,
} from 'lucide-react'
import { importGoogleSearch, listSourceRuns } from '../api/sources'
import { getWorkflowRun, listWorkflows } from '../api/workflows'
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

const SOURCE_COLORS = { google_search: 'teal' }
const ACTIVE_IMPORT_STATUSES = new Set(['pending', 'running'])
const TERMINAL_WORKFLOW_STATUSES = new Set(['completed', 'completed_with_errors', 'failed'])
const SCORE_BATCH_LIMIT = 10

function FlowStep({ number, title, description, accent, active = true }) {
  return (
    <div className="flex gap-3">
      <div
        className={`grid h-9 w-9 flex-shrink-0 place-items-center rounded-lg border text-sm font-extrabold ${
          active ? 'border-ink text-ink shadow-[3px_3px_0_rgba(24,33,47,0.12)]' : 'border-ink/10 text-muted'
        }`}
        style={{ backgroundColor: active ? accent : 'white' }}
      >
        {number}
      </div>
      <div>
        <div className="text-sm font-bold text-ink">{title}</div>
        <p className="mt-0.5 text-xs font-medium leading-5 text-muted">{description}</p>
      </div>
    </div>
  )
}

function RunsTable({ runs }) {
  if (runs.length === 0) {
    return (
      <EmptyState
        icon={History}
        title="No imports yet"
        description="Search ATS boards and your import runs will land here."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-ink/10">
            <th className="px-3 py-2 text-left text-[10px] font-extrabold uppercase tracking-[0.16em] text-muted">Source</th>
            <th className="px-3 py-2 text-left text-[10px] font-extrabold uppercase tracking-[0.16em] text-muted">Status</th>
            <th className="px-3 py-2 text-right text-[10px] font-extrabold uppercase tracking-[0.16em] text-muted">Fetched</th>
            <th className="px-3 py-2 text-right text-[10px] font-extrabold uppercase tracking-[0.16em] text-muted">Stored</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} className="border-b border-ink/5 last:border-0 hover:bg-white/70">
              <td className="px-3 py-3">
                <Badge color={SOURCE_COLORS[run.source_name] ?? 'gray'}>{run.source_name}</Badge>
              </td>
              <td className="px-3 py-3">
                <span className={`text-xs font-extrabold ${run.status === 'success' ? 'text-brand-700' : 'text-rose-600'}`}>
                  {run.status}
                </span>
              </td>
              <td className="px-3 py-3 text-right font-semibold text-muted">{run.jobs_fetched}</td>
              <td className="px-3 py-3 text-right font-display text-lg font-bold text-ink">{run.jobs_stored}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function FindJobs() {
  const queryClient = useQueryClient()

  const [showManual, setShowManual] = useState(false)
  const [manualForm, setManualForm] = useState({ company_name: '', title: '', apply_url: '', location: '', remote_type: '', description: '' })
  const [webSearch, setWebSearch] = useState({ query: 'Software Engineer', location: 'India' })
  const [activeImportRunId, setActiveImportRunId] = useState(null)
  const [scoreProgress, setScoreProgress] = useState({ isRunning: false, remaining: null, scored: 0 })
  const mountedRef = useRef(false)
  const ignoredImportRunIdsRef = useRef(new Set())
  const scoreRunRef = useRef(0)

  const [importMsg, setImportMsg] = useState(null)
  const [scoreMsg, setScoreMsg] = useState(null)
  const [manualMsg, setManualMsg] = useState(null)

  const runsQ = useQuery({ queryKey: ['sourceRuns'], queryFn: () => listSourceRuns({ limit: 20 }) })
  const workflowsQ = useQuery({ queryKey: ['workflows', 'active'], queryFn: () => listWorkflows({ limit: 10 }) })
  const profilesQ = useQuery({ queryKey: ['profiles'], queryFn: () => listProfiles(1, 0) })
  const importRunQ = useQuery({
    queryKey: ['workflowRun', activeImportRunId],
    queryFn: () => getWorkflowRun(activeImportRunId),
    enabled: Boolean(activeImportRunId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && TERMINAL_WORKFLOW_STATUSES.has(status) ? false : 3000
    },
    retry: 3,
  })
  const profile = profilesQ.data?.items?.[0]
  const isImportPolling = Boolean(activeImportRunId)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      scoreRunRef.current += 1
    }
  }, [])

  const onImportSuccess = useCallback((data, name) => {
    queryClient.invalidateQueries({ queryKey: ['sourceRuns'] })
    queryClient.invalidateQueries({ queryKey: ['jobs'] })
    setImportMsg({ type: 'success', message: `${name}: ${data.jobs_stored} new job${data.jobs_stored !== 1 ? 's' : ''} added (${data.jobs_fetched} fetched).` })
  }, [queryClient])

  const onImportError = useCallback((err) => {
    setImportMsg({ type: 'error', message: err.message })
  }, [])

  const webSearchMut = useMutation({
    mutationFn: importGoogleSearch,
    onSuccess: (data) => {
      ignoredImportRunIdsRef.current.delete(data.run_id)
      setActiveImportRunId(data.run_id)
      queryClient.invalidateQueries({ queryKey: ['workflowRun', data.run_id] })
    },
    onError: onImportError,
  })

  useEffect(() => {
    if (activeImportRunId) {
      return
    }

    const activeGoogleWorkflow = workflowsQ.data?.items?.find((workflow) => {
      return (
        workflow.source_name === 'google_search' &&
        ACTIVE_IMPORT_STATUSES.has(workflow.status) &&
        workflow.run_id &&
        !ignoredImportRunIdsRef.current.has(workflow.run_id)
      )
    })

    if (activeGoogleWorkflow?.run_id) {
      setActiveImportRunId(activeGoogleWorkflow.run_id)
    }
  }, [activeImportRunId, workflowsQ.data])

  useEffect(() => {
    if (!activeImportRunId || !importRunQ.data) {
      return
    }

    if (importRunQ.data.status === 'completed') {
      onImportSuccess(getGoogleSearchImportSummary(importRunQ.data), 'Google Search')
      ignoredImportRunIdsRef.current.add(activeImportRunId)
      setActiveImportRunId(null)
      return
    }

    if (TERMINAL_WORKFLOW_STATUSES.has(importRunQ.data.status)) {
      const errorMessage = getWorkflowErrorMessage(importRunQ.data)
      queryClient.invalidateQueries({ queryKey: ['sourceRuns'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setImportMsg({ type: 'error', message: `Web search import ${importRunQ.data.status}: ${errorMessage}` })
      ignoredImportRunIdsRef.current.add(activeImportRunId)
      setActiveImportRunId(null)
    }
  }, [activeImportRunId, importRunQ.data, onImportSuccess, queryClient])

  useEffect(() => {
    if (!activeImportRunId || !importRunQ.isError) {
      return
    }
    setImportMsg({ type: 'error', message: importRunQ.error.message })
    ignoredImportRunIdsRef.current.add(activeImportRunId)
    setActiveImportRunId(null)
  }, [activeImportRunId, importRunQ.error, importRunQ.isError])

  const scoreMut = useMutation({ mutationFn: scoreJobs })
  const isScoring = scoreProgress.isRunning || scoreMut.isPending

  async function scoreAllJobBatches() {
    const runToken = scoreRunRef.current + 1
    scoreRunRef.current = runToken
    let totalScored = 0
    let remaining = null

    setScoreMsg(null)
    setScoreProgress({ isRunning: true, remaining: null, scored: 0 })

    try {
      do {
        const data = await scoreMut.mutateAsync({ limit: SCORE_BATCH_LIMIT })
        if (!mountedRef.current || scoreRunRef.current !== runToken) {
          return
        }

        const batchScored = Number(data.scored_count ?? data.scored ?? 0)
        remaining = Number(data.remaining_unscored_count ?? 0)
        totalScored += batchScored
        setScoreProgress({ isRunning: remaining > 0, remaining, scored: totalScored })
      } while (remaining > 0)

      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      if (totalScored === 0) {
        setScoreMsg({ type: 'success', message: 'All jobs already scored. Job Matches is ready.' })
      } else {
        setScoreMsg({ type: 'success', message: `Scored ${totalScored} jobs against your profile.` })
      }
    } catch (err) {
      if (!mountedRef.current || scoreRunRef.current !== runToken) {
        return
      }
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setScoreMsg({
        type: 'error',
        message: `Scoring paused after ${totalScored} job${totalScored !== 1 ? 's' : ''}: ${err.message}`,
      })
    } finally {
      if (mountedRef.current && scoreRunRef.current === runToken) {
        setScoreProgress((progress) => ({ ...progress, isRunning: false }))
      }
    }
  }

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

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="mb-6 grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-muted">Source lab</p>
          <h1 className="mt-1 font-display text-4xl font-bold leading-tight text-ink">Find jobs</h1>
          <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-muted">
            Pull in roles, score them, and keep the manual saves from getting lost.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 rounded-lg border border-ink/10 bg-white p-2">
          <FlowStep number="1" title="Import" description="ATS sweep" accent="#67b7f7" />
          <FlowStep number="2" title="Score" description="Profile fit" accent="#f7c948" active={Boolean(profile)} />
          <FlowStep number="3" title="Capture" description="Manual leads" accent="#53d0a2" active={false} />
        </div>
      </header>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
        <div className="space-y-5">
          <Card accent="var(--sky)" className="p-0">
            <div className="grid gap-0 lg:grid-cols-[1fr_250px]">
              <div className="p-5">
                <CardHeader
                  eyebrow="ATS sweep"
                  title="Direct web search"
                  subtitle="Greenhouse, Lever, Workday, Ashby, and iCIMS sources."
                  action={<Badge color="blue">Live import</Badge>}
                />

                {importMsg?.type === 'success' && <SuccessMessage message={importMsg.message} className="mb-4" />}
                {importMsg?.type === 'error' && <ErrorMessage message={importMsg.message} className="mb-4" />}

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_0.75fr_auto] sm:items-end">
                  <Input
                    label="Role"
                    value={webSearch.query}
                    onChange={(e) => setWebSearch((s) => ({ ...s, query: e.target.value }))}
                    disabled={webSearchMut.isPending || isImportPolling}
                  />
                  <Input
                    label="Location"
                    value={webSearch.location}
                    onChange={(e) => setWebSearch((s) => ({ ...s, location: e.target.value }))}
                    disabled={webSearchMut.isPending || isImportPolling}
                  />
                  <Button
                    variant="sun"
                    loading={webSearchMut.isPending || isImportPolling}
                    disabled={isImportPolling || !webSearch.query.trim() || !webSearch.location.trim()}
                    onClick={() => { setImportMsg(null); webSearchMut.mutate(webSearch) }}
                  >
                    <Search className="h-4 w-4" />
                    Search
                  </Button>
                </div>

                {isImportPolling && (
                  <div className="mt-4 flex items-center gap-2 rounded-lg border border-sun/40 bg-sun/20 px-4 py-3 text-sm font-bold text-amber-900">
                    <Clock3 className="h-4 w-4" />
                    Searching ATS boards. This may take a few seconds.
                  </div>
                )}
              </div>

              <div className="ink-surface ticket-edge border-t p-5 lg:border-l lg:border-t-0">
                <div className="ink-icon-tile subtle-bob grid h-14 w-14 place-items-center rounded-lg">
                  <Search className="h-7 w-7" />
                </div>
                <p className="mt-5 font-display text-2xl font-bold leading-tight">Sweep first, sort second.</p>
                <p className="ink-muted mt-2 text-sm font-medium leading-6">
                  Imported jobs stay separate until scoring, so you can review the pipeline calmly.
                </p>
              </div>
            </div>
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card accent="var(--sun)">
              <div className="flex h-full flex-col">
                <CardHeader
                  eyebrow="Fit engine"
                  title="Score against profile"
                  subtitle={profile ? 'Your extracted profile is ready.' : 'Upload a resume before scoring.'}
                  action={<Zap className="h-5 w-5 text-amber-600" />}
                />
                <p className="text-sm font-medium leading-6 text-muted">
                  Match scoring ranks imported roles by skills, experience, and target role alignment.
                </p>
                {!profile && (
                  <div className="mt-4 rounded-lg border border-coral/25 bg-coral/10 px-3 py-2 text-xs font-bold text-rose-700">
                    Resume profile required.
                  </div>
                )}
                {scoreMsg?.type === 'success' && <SuccessMessage message={scoreMsg.message} className="mt-4" />}
                {scoreMsg?.type === 'error' && <ErrorMessage message={scoreMsg.message} className="mt-4" />}
                <div className="mt-auto pt-5">
                  <Button
                    onClick={scoreAllJobBatches}
                    loading={isScoring}
                    disabled={!profile || isScoring}
                    className="w-full"
                  >
                    <Sparkles className="h-4 w-4" />
                    {isScoring && scoreProgress.remaining !== null
                      ? `Scoring ${scoreProgress.remaining} left`
                      : isScoring
                        ? 'Scoring'
                        : 'Score jobs'}
                  </Button>
                </div>
              </div>
            </Card>

            <Card accent="var(--mint)">
              <button
                className="flex w-full items-start justify-between gap-4 text-left"
                onClick={() => setShowManual((v) => !v)}
              >
                <div>
                  <p className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-muted">Manual capture</p>
                  <h2 className="mt-1 font-display text-xl font-bold text-ink">Add a job by hand</h2>
                  <p className="mt-1 text-sm font-medium leading-6 text-muted">
                    Paste a promising role from anywhere and send it into matching.
                  </p>
                </div>
                <div className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-lg border border-ink/10 bg-white text-ink">
                  {showManual ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </div>
              </button>

              {showManual && (
                <div className="mt-5 space-y-4 border-t border-ink/10 pt-5">
                  {manualMsg?.type === 'success' && <SuccessMessage message={manualMsg.message} />}
                  {manualMsg?.type === 'error' && <ErrorMessage message={manualMsg.message} />}
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <Input label="Company" placeholder="Acme Corp" value={manualForm.company_name} onChange={(e) => setManualForm((f) => ({ ...f, company_name: e.target.value }))} />
                    <Input label="Title" placeholder="Software Engineer" value={manualForm.title} onChange={(e) => setManualForm((f) => ({ ...f, title: e.target.value }))} />
                    <Input label="Apply link" placeholder="https://..." value={manualForm.apply_url} onChange={(e) => setManualForm((f) => ({ ...f, apply_url: e.target.value }))} />
                    <Input label="Location" placeholder="Remote, Bengaluru, etc." value={manualForm.location} onChange={(e) => setManualForm((f) => ({ ...f, location: e.target.value }))} />
                    <Select label="Work mode" value={manualForm.remote_type} onChange={(e) => setManualForm((f) => ({ ...f, remote_type: e.target.value }))}>
                      <option value="">Not specified</option>
                      <option value="remote">Remote</option>
                      <option value="hybrid">Hybrid</option>
                      <option value="onsite">On-site</option>
                    </Select>
                  </div>
                  <Textarea label="Description" placeholder="Paste the job description here..." rows={5} value={manualForm.description} onChange={(e) => setManualForm((f) => ({ ...f, description: e.target.value }))} />
                  <div className="flex justify-end">
                    <Button
                      onClick={() => { setManualMsg(null); manualMut.mutate() }}
                      loading={manualMut.isPending}
                      disabled={!manualForm.company_name || !manualForm.title || !manualForm.apply_url || !manualForm.description}
                    >
                      <Plus className="h-4 w-4" />
                      Add job
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>

        <aside className="xl:sticky xl:top-8 xl:self-start">
          <Card accent="var(--coral)">
            <CardHeader
              eyebrow="History"
              title="Import runs"
              subtitle="Last 20 source runs"
              action={<ListChecks className="h-5 w-5 text-muted" />}
            />
            {runsQ.isLoading ? <PageSpinner /> : <RunsTable runs={runs} />}
          </Card>
        </aside>
      </div>
    </div>
  )
}

function getGoogleSearchImportSummary(workflowRun) {
  const sourceResult = workflowRun.state?.source_results?.find((result) => result.source_name === 'google_search') ?? {}
  return {
    jobs_fetched: Number(sourceResult.jobs_fetched ?? 0),
    jobs_stored: Number(sourceResult.jobs_stored ?? 0),
  }
}

function getWorkflowErrorMessage(workflowRun) {
  const sourceError = workflowRun.state?.source_results?.find((result) => result.error_message)?.error_message
  const workflowError = workflowRun.errors?.[0]?.message
  return sourceError || workflowError || 'Check the workflow run for details.'
}
