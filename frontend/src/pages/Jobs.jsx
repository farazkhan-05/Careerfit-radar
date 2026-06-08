import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, BookmarkPlus, Trash2, Zap } from 'lucide-react'
import { listJobs, deleteJob, deleteAllJobs } from '../api/jobs'
import { saveJob } from '../api/applications'
import { Card } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Input, Select } from '../components/ui/Input'
import { SourceBadge, StatusBadge } from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'
import ErrorMessage, { SuccessMessage } from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'
import { Link } from 'react-router-dom'

const PAGE_SIZE = 25

function MatchScoreBadge({ score }) {
  if (score == null) return null
  const color = score >= 70 ? 'bg-emerald-100 text-emerald-700' : score >= 50 ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${color}`}>
      ⚡ {score}% match
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

  return (
    <Card className="hover:shadow-md transition-shadow duration-150">
      <div className="flex items-start gap-4">
        <div className={`h-10 w-1 rounded-full flex-shrink-0 mt-1 ${
          job.match_score >= 70 ? 'bg-gradient-to-b from-emerald-400 to-teal-400'
          : job.match_score >= 50 ? 'bg-gradient-to-b from-amber-400 to-orange-400'
          : 'bg-gradient-to-b from-brand-400 to-indigo-400'
        }`} />

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className="text-sm font-semibold text-slate-900 leading-snug">{job.title}</h3>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <MatchScoreBadge score={job.match_score} />
              <StatusBadge status={job.status} />
              <button
                onClick={() => onDelete(job.id)}
                disabled={deleting}
                className="p-1 text-slate-300 hover:text-rose-500 transition-colors"
                title="Delete job"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 mb-3">
            <SourceBadge source={job.source} />
            {job.location && <span className="text-xs text-slate-500">📍 {job.location}</span>}
            {job.remote_type && (
              <span className="text-xs text-slate-500 capitalize">
                {job.remote_type === 'remote' ? '🌍' : job.remote_type === 'hybrid' ? '🔀' : '🏢'} {job.remote_type}
              </span>
            )}
            {job.posted_at && (
              <span className="text-xs text-slate-400">
                {new Date(job.posted_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
              </span>
            )}
          </div>

          {job.description && (
            <p className="text-xs text-slate-500 line-clamp-2 mb-3">{job.description}</p>
          )}

          {job.match_explanation && (
            <div className="mb-3">
              <button onClick={() => setShowExplanation(v => !v)} className="text-xs text-brand-600 hover:text-brand-700 underline-offset-2 hover:underline">
                {showExplanation ? 'Hide' : 'Why this score?'}
              </button>
              {showExplanation && (
                <p className="mt-1.5 text-xs text-slate-500 bg-slate-50 rounded-lg p-2.5">{job.match_explanation}</p>
              )}
            </div>
          )}

          <div className="flex items-center gap-2">
            <Button variant={saved ? 'success' : 'secondary'} size="sm" loading={saving} disabled={saved || job.status === 'saved'} onClick={handleSave}>
              <BookmarkPlus className="h-3.5 w-3.5" />
              {saved || job.status === 'saved' ? 'Saved' : 'Save'}
            </Button>
            <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-brand-600 hover:bg-brand-700 text-white transition-colors">
              Apply <ExternalLink className="h-3 w-3" />
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
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Job Matches</h1>
          <p className="text-slate-500 mt-1">Browse and save jobs that match your profile</p>
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
            className="text-rose-500 hover:text-rose-600 hover:bg-rose-50 mt-1"
          >
            <Trash2 className="h-3.5 w-3.5 mr-1" />
            Delete All
          </Button>
        )}
      </div>

      {saveMsg?.type === 'success' && <SuccessMessage message={saveMsg.message} className="mb-4" />}
      {saveMsg?.type === 'error' && <ErrorMessage message={saveMsg.message} className="mb-4" />}

      {/* Filters */}
      <Card className="mb-5">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-48">
            <Input
              placeholder="Search job titles…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setOffset(0) }}
            />
          </div>
          <div className="w-36">
            <Select value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0) }}>
              <option value="">All statuses</option>
              <option value="new">New</option>
              <option value="saved">Saved</option>
              <option value="rejected">Rejected</option>
            </Select>
          </div>
          <div className="w-36">
            <Select value={source} onChange={(e) => { setSource(e.target.value); setOffset(0) }}>
              <option value="">All sources</option>
              <option value="apify">Apify</option>
              <option value="manual">Manual</option>
            </Select>
          </div>
          <button
            onClick={() => { setTopMatches(v => !v); setOffset(0) }}
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
              topMatches ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-slate-600 border-slate-200 hover:border-amber-300'
            }`}
          >
            <Zap className="h-3.5 w-3.5" />
            Top Matches
          </button>
        </div>
      </Card>

      {/* Count */}
      {!jobsQ.isLoading && (
        <div className="text-sm text-slate-500 mb-4">
          {total} job{total !== 1 ? 's' : ''} found
        </div>
      )}

      {/* Jobs list */}
      {jobsQ.isLoading ? (
        <PageSpinner />
      ) : jobs.length === 0 ? (
        <EmptyState
          icon="🔍"
          title="No jobs found"
          description="Try adjusting your filters or import jobs from a source."
          action={
            <Link to="/find-jobs">
              <Button>Find Jobs</Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-3">
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

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <Button
            variant="secondary"
            size="sm"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            ← Previous
          </Button>
          <span className="text-sm text-slate-500">
            Page {currentPage} of {totalPages}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next →
          </Button>
        </div>
      )}
    </div>
  )
}
