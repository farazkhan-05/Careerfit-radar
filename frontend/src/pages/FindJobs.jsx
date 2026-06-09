import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, ChevronUp, Plus, Sparkles, Zap } from 'lucide-react'
import { importApify, listSourceRuns } from '../api/sources'
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

const SOURCE_COLORS = { apify: 'teal' }
const ACTIVE_IMPORT_STATUSES = new Set(['pending', 'running'])
const TERMINAL_WORKFLOW_STATUSES = new Set(['completed', 'completed_with_errors', 'failed'])
const SCORE_BATCH_LIMIT = 10

function RunsTable({ runs }) {
  if (runs.length === 0) {
    return (
      <EmptyState icon="list" title="No imports yet" description="Import jobs from Apify to get started." />
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

  const [showManual, setShowManual] = useState(false)
  const [manualForm, setManualForm] = useState({ company_name: '', title: '', apply_url: '', location: '', remote_type: '', description: '' })
  const [apifySearch, setApifySearch] = useState({ query: 'Software Engineer', location: 'India' })
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
  const apifyRunQ = useQuery({
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
  const isApifyPolling = Boolean(activeImportRunId)

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

  const apifyMut = useMutation({
    mutationFn: importApify,
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

    const activeApifyWorkflow = workflowsQ.data?.items?.find((workflow) => {
      return (
        workflow.source_name === 'apify' &&
        ACTIVE_IMPORT_STATUSES.has(workflow.status) &&
        workflow.run_id &&
        !ignoredImportRunIdsRef.current.has(workflow.run_id)
      )
    })

    if (activeApifyWorkflow?.run_id) {
      setActiveImportRunId(activeApifyWorkflow.run_id)
    }
  }, [activeImportRunId, workflowsQ.data])

  useEffect(() => {
    if (!activeImportRunId || !apifyRunQ.data) {
      return
    }

    if (apifyRunQ.data.status === 'completed') {
      onImportSuccess(getApifyImportSummary(apifyRunQ.data), 'Apify')
      ignoredImportRunIdsRef.current.add(activeImportRunId)
      setActiveImportRunId(null)
      return
    }

    if (TERMINAL_WORKFLOW_STATUSES.has(apifyRunQ.data.status)) {
      const errorMessage = getWorkflowErrorMessage(apifyRunQ.data)
      queryClient.invalidateQueries({ queryKey: ['sourceRuns'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setImportMsg({ type: 'error', message: `Apify import ${apifyRunQ.data.status}: ${errorMessage}` })
      ignoredImportRunIdsRef.current.add(activeImportRunId)
      setActiveImportRunId(null)
    }
  }, [activeImportRunId, apifyRunQ.data, onImportSuccess, queryClient])

  useEffect(() => {
    if (!activeImportRunId || !apifyRunQ.isError) {
      return
    }
    setImportMsg({ type: 'error', message: apifyRunQ.error.message })
    ignoredImportRunIdsRef.current.add(activeImportRunId)
    setActiveImportRunId(null)
  }, [activeImportRunId, apifyRunQ.error, apifyRunQ.isError])

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
        setScoreMsg({ type: 'success', message: 'All jobs already scored. Go to Job Matches to see results.' })
      } else {
        setScoreMsg({ type: 'success', message: `Scored ${totalScored} jobs against your profile. Go to Job Matches to see results sorted by fit.` })
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
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Find Jobs</h1>
        <p className="text-slate-500 mt-1">Import jobs, then score them against your resume with AI</p>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="h-7 w-7 rounded-full bg-brand-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">1</div>
        <h2 className="text-base font-semibold text-slate-800">Import jobs</h2>
      </div>

      {importMsg?.type === 'success' && <SuccessMessage message={importMsg.message} className="mb-4" />}
      {importMsg?.type === 'error' && <ErrorMessage message={importMsg.message} className="mb-4" />}

      <Card className="mb-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="text-sm font-semibold text-slate-800">
                Apify <span className="text-xs font-normal text-emerald-600 ml-1">LinkedIn</span>
              </div>
              <div className="text-xs text-slate-500">Fresh entry-level roles from your search</div>
            </div>
            <Button
              loading={apifyMut.isPending || isApifyPolling}
              disabled={isApifyPolling || !apifySearch.query.trim() || !apifySearch.location.trim()}
              onClick={() => { setImportMsg(null); apifyMut.mutate(apifySearch) }}
            >
              Import
            </Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Search Query"
              value={apifySearch.query}
              onChange={(e) => setApifySearch((search) => ({ ...search, query: e.target.value }))}
              disabled={apifyMut.isPending || isApifyPolling}
            />
            <Input
              label="Location"
              value={apifySearch.location}
              onChange={(e) => setApifySearch((search) => ({ ...search, location: e.target.value }))}
              disabled={apifyMut.isPending || isApifyPolling}
            />
          </div>
          {isApifyPolling && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Scraping in progress... this may take a few minutes
            </div>
          )}
        </div>
      </Card>

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
            onClick={scoreAllJobBatches}
            loading={isScoring}
            disabled={!profile || isScoring}
            className="flex-shrink-0"
          >
            <Sparkles className="h-4 w-4" />
            {isScoring && scoreProgress.remaining !== null
              ? `Scoring batch... ${scoreProgress.remaining} remaining`
              : isScoring
                ? 'Scoring batch...'
                : 'Score Jobs'}
          </Button>
        </div>
        {scoreMsg?.type === 'success' && <SuccessMessage message={scoreMsg.message} className="mt-3" />}
        {scoreMsg?.type === 'error' && <ErrorMessage message={scoreMsg.message} className="mt-3" />}
      </Card>

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
            <Textarea label="Job Description" placeholder="Paste the job description here..." rows={4} value={manualForm.description} onChange={(e) => setManualForm(f => ({ ...f, description: e.target.value }))} />
            <div className="flex justify-end">
              <Button onClick={() => { setManualMsg(null); manualMut.mutate() }} loading={manualMut.isPending} disabled={!manualForm.company_name || !manualForm.title || !manualForm.apply_url || !manualForm.description}>
                Add Job
              </Button>
            </div>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Import History" subtitle="Last 20 source runs" />
        {runsQ.isLoading ? <PageSpinner /> : <RunsTable runs={runs} />}
      </Card>
    </div>
  )
}

function getApifyImportSummary(workflowRun) {
  const sourceResult = workflowRun.state?.source_results?.find((result) => result.source_name === 'apify') ?? {}
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
