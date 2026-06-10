import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BookmarkPlus,
  Building2,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  MapPin,
  Search,
  SlidersHorizontal,
  Trash2,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { listJobs, deleteJob, deleteAllJobs } from '../api/jobs'
import { saveJob } from '../api/applications'
import { Card, CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Input, Select } from '../components/ui/Input'
import { SourceBadge, StatusBadge } from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'
import ErrorMessage, { SuccessMessage } from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'

const PAGE_SIZE = 25

function MatchScoreBadge({ score }) {
  if (score == null) return null
  const tone =
    score >= 70
      ? 'border-brand-500/25 bg-brand-100 text-brand-800'
      : score >= 50
        ? 'border-sun/40 bg-sun/20 text-amber-800'
        : 'border-sky/30 bg-sky/15 text-blue-700'

  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-extrabold ${tone}`}>
      <Zap className="h-3 w-3" />
      {score}% match
    </span>
  )
}

function MetaItem({ icon: Icon, children }) {
  if (!children) return null
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted">
      <Icon className="h-3.5 w-3.5" />
      {children}
    </span>
  )
}

function JobCard({ job, onSave, saving, onDelete, deleting }) {
  const [saved, setSaved] = useState(false)
  const [showExplanation, setShowExplanation] = useState(false)

  async function handleSave() {
    await onSave(job.id)
    setSaved(true)
  }

  const scoreAccent = job.match_score >= 70 ? 'var(--mint)' : job.match_score >= 50 ? 'var(--sun)' : 'var(--sky)'

  return (
    <Card
      accent={scoreAccent}
      className="transition-all duration-150 hover:-translate-y-1 hover:shadow-[8px_8px_0_rgba(24,33,47,0.10)]"
    >
      <div className="grid gap-4 md:grid-cols-[56px_1fr]">
        <div className="grid h-14 w-14 place-items-center rounded-lg border border-ink/10 bg-white text-lg font-extrabold text-ink shadow-[4px_4px_0_rgba(24,33,47,0.08)]">
          {(job.company_name || job.title || '?').charAt(0).toUpperCase()}
        </div>

        <div className="min-w-0">
          <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-start">
            <div className="min-w-0">
              <h3 className="font-display text-xl font-bold leading-tight text-ink">{job.title}</h3>
              <div className="mt-1 flex items-center gap-1.5 text-sm font-bold text-muted">
                <Building2 className="h-4 w-4" />
                <span className="truncate">{job.company_name || 'Company not listed'}</span>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 lg:justify-end">
              <MatchScoreBadge score={job.match_score} />
              <StatusBadge status={job.status} />
              <button
                onClick={() => onDelete(job.id)}
                disabled={deleting}
                className="rounded-lg border border-transparent p-2 text-muted transition-colors hover:border-coral/25 hover:bg-coral/10 hover:text-rose-700 disabled:opacity-50"
                title="Delete job"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
            <SourceBadge source={job.source} />
            <MetaItem icon={MapPin}>{job.location}</MetaItem>
            <MetaItem icon={Building2}>{job.remote_type ? job.remote_type.charAt(0).toUpperCase() + job.remote_type.slice(1) : null}</MetaItem>
            <MetaItem icon={CalendarDays}>
              {job.posted_at
                ? new Date(job.posted_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
                : null}
            </MetaItem>
          </div>

          {job.description && (
            <p className="mt-4 line-clamp-2 text-sm font-medium leading-6 text-muted">{job.description}</p>
          )}

          {job.match_explanation && (
            <div className="mt-4">
              <button
                onClick={() => setShowExplanation((v) => !v)}
                className="text-sm font-bold text-ink underline decoration-brand-400 decoration-2 underline-offset-4 hover:text-brand-700"
              >
                {showExplanation ? 'Hide score notes' : 'Why this score?'}
              </button>
              {showExplanation && (
                <p className="mt-3 rounded-lg border border-ink/10 bg-white px-4 py-3 text-sm font-medium leading-6 text-muted">
                  {job.match_explanation}
                </p>
              )}
            </div>
          )}

          <div className="mt-5 flex flex-wrap items-center gap-2">
            <Button
              variant={saved || job.status === 'saved' ? 'success' : 'secondary'}
              size="sm"
              loading={saving}
              disabled={saved || job.status === 'saved'}
              onClick={handleSave}
            >
              <BookmarkPlus className="h-4 w-4" />
              {saved || job.status === 'saved' ? 'Saved' : 'Save'}
            </Button>
            <a
              href={job.apply_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-h-8 items-center justify-center gap-2 rounded-lg border border-ink bg-ink px-3 py-1.5 text-xs font-bold text-white transition-all duration-150 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:bg-[#0f1722] hover:shadow-button active:translate-x-0 active:translate-y-0 active:shadow-none"
            >
              Apply
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      </div>
    </Card>
  )
}

export default function Jobs() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [source, setSource] = useState('')
  const [topMatches, setTopMatches] = useState(false)
  const [offset, setOffset] = useState(0)
  const [saveMsg, setSaveMsg] = useState(null)

  const params = { limit: PAGE_SIZE, offset, q: search || undefined, status: status || undefined, source: source || undefined, top_matches: topMatches || undefined }

  const jobsQ = useQuery({
    queryKey: ['jobs', params],
    queryFn: () => listJobs(params),
  })

  const saveMut = useMutation({
    mutationFn: (jobId) => saveJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      setSaveMsg({ type: 'success', message: 'Job saved to your applications.' })
    },
    onError: (err) => setSaveMsg({ type: 'error', message: err.message }),
  })

  const deleteMut = useMutation({
    mutationFn: (jobId) => deleteJob(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
    onError: (err) => setSaveMsg({ type: 'error', message: err.message }),
  })

  const deleteAllMut = useMutation({
    mutationFn: deleteAllJobs,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['sourceRuns'] })
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      setSaveMsg({ type: 'success', message: 'All jobs deleted.' })
    },
    onError: (err) => setSaveMsg({ type: 'error', message: err.message }),
  })

  const jobs = jobsQ.data?.items ?? []
  const total = jobsQ.data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-muted">Shortlist</p>
          <h1 className="mt-1 font-display text-4xl font-bold leading-tight text-ink">Job matches</h1>
          <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-muted">
            Browse scored jobs, save the strongest roles, and clear noise fast.
          </p>
        </div>
        {total > 0 && (
          <Button
            variant="ghost"
            size="sm"
            loading={deleteAllMut.isPending}
            onClick={() => {
              if (window.confirm(`Delete all ${total} jobs? This cannot be undone.`)) {
                deleteAllMut.mutate()
              }
            }}
            className="text-rose-600 hover:bg-coral/10 hover:text-rose-700"
          >
            <Trash2 className="h-4 w-4" />
            Delete all
          </Button>
        )}
      </header>

      {saveMsg?.type === 'success' && <SuccessMessage message={saveMsg.message} className="mb-4" />}
      {saveMsg?.type === 'error' && <ErrorMessage message={saveMsg.message} className="mb-4" />}

      <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
        <aside className="lg:sticky lg:top-8 lg:self-start">
          <Card accent="var(--sky)">
            <CardHeader
              eyebrow="Controls"
              title="Filters"
              subtitle={`${total} job${total !== 1 ? 's' : ''} found`}
              action={<SlidersHorizontal className="h-5 w-5 text-muted" />}
            />
            <div className="space-y-4">
              <Input
                label="Search"
                placeholder="Search job titles..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setOffset(0) }}
              />
              <Select label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0) }}>
                <option value="">All statuses</option>
                <option value="new">New</option>
                <option value="saved">Saved</option>
                <option value="rejected">Rejected</option>
              </Select>
              <Select label="Source" value={source} onChange={(e) => { setSource(e.target.value); setOffset(0) }}>
                <option value="">All sources</option>
                <option value="tavily_search">Web Search</option>
                <option value="google_search">Google Search (legacy)</option>
                <option value="manual">Manual</option>
              </Select>
              <button
                onClick={() => { setTopMatches((v) => !v); setOffset(0) }}
                className={`flex w-full items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-bold transition-all duration-150 hover:-translate-y-0.5 hover:shadow-button ${
                  topMatches
                    ? 'border-ink bg-sun text-ink'
                    : 'border-ink/15 bg-white text-muted hover:border-ink hover:text-ink'
                }`}
              >
                <Zap className="h-4 w-4" />
                Top matches
              </button>
            </div>
          </Card>
        </aside>

        <section>
          {jobsQ.isLoading ? (
            <PageSpinner />
          ) : jobs.length === 0 ? (
            <EmptyState
              icon={Search}
              title="No jobs found"
              description="Adjust the filters or import fresh jobs from a source."
              action={
                <Link to="/find-jobs">
                  <Button>Find jobs</Button>
                </Link>
              }
            />
          ) : (
            <div className="space-y-4">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  onSave={(id) => saveMut.mutateAsync(id)}
                  saving={saveMut.isPending && saveMut.variables === job.id}
                  onDelete={(id) => deleteMut.mutate(id)}
                  deleting={deleteMut.isPending && deleteMut.variables === job.id}
                />
              ))}
            </div>
          )}

          {totalPages > 1 && (
            <div className="mt-6 flex flex-col gap-3 rounded-lg border border-ink/10 bg-white/80 p-3 sm:flex-row sm:items-center sm:justify-between">
              <Button
                variant="secondary"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <span className="text-center text-sm font-bold text-muted">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
