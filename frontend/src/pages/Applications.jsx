import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CalendarDays, ClipboardList, FilterX, Pencil, Save, StickyNote, Trash2, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { listApplications, updateApplication, deleteApplication, deleteAllApplications } from '../api/applications'
import { Card } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Select, Textarea } from '../components/ui/Input'
import { StatusBadge } from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'
import ErrorMessage, { SuccessMessage } from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'

const STATUSES = ['saved', 'applied', 'follow_up', 'interview', 'offer', 'rejected', 'ignored']

const STATUS_ACCENTS = {
  saved: 'var(--plum)',
  applied: 'var(--sky)',
  follow_up: 'var(--sun)',
  interview: 'var(--sun)',
  offer: 'var(--mint)',
  rejected: 'var(--coral)',
  ignored: '#cbd5e1',
}

function formatDate(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function humanize(status) {
  return status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')
}

function DateTag({ label, value }) {
  if (!value) return null
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-ink/10 bg-white px-2 py-1 text-xs font-bold text-muted">
      <CalendarDays className="h-3.5 w-3.5" />
      {label}: {formatDate(value)}
    </span>
  )
}

function ApplicationCard({ application, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [status, setStatus] = useState(application.status)
  const [notes, setNotes] = useState(application.notes ?? '')
  const [msg, setMsg] = useState(null)

  async function handleSave() {
    try {
      setMsg(null)
      await onUpdate(application.id, { status, notes: notes || null })
      setMsg({ type: 'success', message: 'Updated.' })
      setEditing(false)
    } catch (err) {
      setMsg({ type: 'error', message: err.message })
    }
  }

  return (
    <Card accent={STATUS_ACCENTS[application.status] ?? 'var(--sky)'} className="h-full">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={application.status} />
            <span className="truncate rounded-md bg-white px-2 py-1 text-xs font-mono font-bold text-muted">
              {application.job_id}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            <DateTag label="Saved" value={application.created_at} />
            <DateTag label="Applied" value={application.applied_at} />
            <DateTag label="Follow up" value={application.follow_up_at} />
          </div>
        </div>
        <div className="flex flex-shrink-0 items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setEditing((v) => !v)}
            className="text-muted"
            title="Edit application"
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(application.id)}
            className="text-rose-600 hover:bg-coral/10 hover:text-rose-700"
            title="Delete application"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {application.notes && !editing && (
        <p className="rounded-lg border border-ink/10 bg-white px-4 py-3 text-sm font-medium leading-6 text-muted">
          <StickyNote className="mr-2 inline h-4 w-4" />
          {application.notes}
        </p>
      )}

      {editing && (
        <div className="space-y-4 border-t border-ink/10 pt-4">
          {msg?.type === 'success' && <SuccessMessage message={msg.message} />}
          {msg?.type === 'error' && <ErrorMessage message={msg.message} />}
          <Select
            label="Status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {humanize(s)}
              </option>
            ))}
          </Select>
          <Textarea
            label="Notes"
            placeholder="Add notes about this application..."
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>
              <X className="h-4 w-4" />
              Cancel
            </Button>
            <Button size="sm" onClick={handleSave}>
              <Save className="h-4 w-4" />
              Save
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}

export default function Applications() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [deleteMsg, setDeleteMsg] = useState(null)

  const appsQ = useQuery({
    queryKey: ['applications', statusFilter],
    queryFn: () => listApplications({ limit: 100, status: statusFilter || undefined }),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, patch }) => updateApplication(id, patch),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['applications'] }),
  })

  const deleteMut = useMutation({
    mutationFn: (id) => deleteApplication(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      setDeleteMsg({ type: 'success', message: 'Application removed.' })
    },
    onError: (err) => setDeleteMsg({ type: 'error', message: err.message }),
  })

  const deleteAllMut = useMutation({
    mutationFn: deleteAllApplications,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      setDeleteMsg({ type: 'success', message: 'All applications deleted.' })
    },
    onError: (err) => setDeleteMsg({ type: 'error', message: err.message }),
  })

  const applications = appsQ.data?.items ?? []
  const total = appsQ.data?.total ?? 0

  const statusCounts = applications.reduce((acc, application) => {
    acc[application.status] = (acc[application.status] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-muted">Pipeline</p>
          <h1 className="mt-1 font-display text-4xl font-bold leading-tight text-ink">Applications</h1>
          <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-muted">
            Keep saved roles, follow-ups, interviews, and notes visible.
          </p>
        </div>
        {total > 0 && (
          <Button
            variant="ghost"
            size="sm"
            loading={deleteAllMut.isPending}
            onClick={() => {
              if (window.confirm(`Delete all ${total} applications? This cannot be undone.`)) {
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

      {deleteMsg?.type === 'success' && <SuccessMessage message={deleteMsg.message} className="mb-4" />}
      {deleteMsg?.type === 'error' && <ErrorMessage message={deleteMsg.message} className="mb-4" />}

      {total > 0 && (
        <Card accent="var(--plum)" className="mb-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-muted">Status board</p>
              <h2 className="font-display text-xl font-bold text-ink">
                {total} application{total !== 1 ? 's' : ''}{statusFilter ? ` - ${humanize(statusFilter)}` : ''}
              </h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(statusCounts).map(([statusName, count]) => (
                <button
                  key={statusName}
                  onClick={() => setStatusFilter(statusFilter === statusName ? '' : statusName)}
                  className={`rounded-lg border px-3 py-2 text-xs font-extrabold transition-all duration-150 hover:-translate-y-0.5 hover:shadow-button ${
                    statusFilter === statusName
                      ? 'ink-surface'
                      : 'border-ink/10 bg-white text-muted hover:border-ink hover:text-ink'
                  }`}
                >
                  {humanize(statusName)} - {count}
                </button>
              ))}
              {statusFilter && (
                <button
                  onClick={() => setStatusFilter('')}
                  className="inline-flex items-center gap-1 rounded-lg border border-ink/10 bg-white px-3 py-2 text-xs font-extrabold text-muted hover:border-ink hover:text-ink"
                >
                  <FilterX className="h-3.5 w-3.5" />
                  Clear
                </button>
              )}
            </div>
          </div>
        </Card>
      )}

      {appsQ.isLoading ? (
        <PageSpinner />
      ) : applications.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No applications yet"
          description="Save a job to start tracking your pipeline here."
          action={
            <Link to="/jobs">
              <Button>Browse jobs</Button>
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {applications.map((application) => (
            <ApplicationCard
              key={application.id}
              application={application}
              onUpdate={(id, patch) => updateMut.mutateAsync({ id, patch })}
              onDelete={(id) => deleteMut.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
