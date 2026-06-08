import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Pencil, Trash2 } from 'lucide-react'
import { listApplications, updateApplication, deleteApplication, deleteAllApplications } from '../api/applications'
import { Card } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Select, Textarea } from '../components/ui/Input'
import { StatusBadge } from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'
import ErrorMessage, { SuccessMessage } from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'
import { Link } from 'react-router-dom'

const STATUSES = ['saved', 'applied', 'follow_up', 'interview', 'offer', 'rejected', 'ignored']

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
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
    <Card>
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge status={application.status} />
            <span className="text-xs text-slate-400 font-mono truncate">{application.job_id}</span>
          </div>
          <div className="flex flex-wrap gap-4 text-xs text-slate-500">
            <span>Saved: {formatDate(application.created_at)}</span>
            {application.applied_at && <span>Applied: {formatDate(application.applied_at)}</span>}
            {application.follow_up_at && <span>Follow up: {formatDate(application.follow_up_at)}</span>}
          </div>
          {application.notes && !editing && (
            <p className="text-xs text-slate-500 mt-2 bg-slate-50 rounded p-2">{application.notes}</p>
          )}
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setEditing((v) => !v)}
            className="text-slate-500"
          >
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(application.id)}
            className="text-rose-400 hover:text-rose-600 hover:bg-rose-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {editing && (
        <div className="border-t border-slate-100 pt-3 space-y-3">
          {msg?.type === 'success' && <SuccessMessage message={msg.message} />}
          {msg?.type === 'error' && <ErrorMessage message={msg.message} />}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1).replace('_', ' ')}
                </option>
              ))}
            </Select>
          </div>
          <Textarea
            label="Notes"
            placeholder="Add notes about this application…"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleSave}>
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

  const statusCounts = applications.reduce((acc, a) => {
    acc[a.status] = (acc[a.status] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Applications</h1>
          <p className="text-slate-500 mt-1">Track your job applications and follow-ups</p>
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
            className="text-rose-500 hover:text-rose-600 hover:bg-rose-50 mt-1"
          >
            <Trash2 className="h-3.5 w-3.5 mr-1" />
            Delete All
          </Button>
        )}
      </div>

      {deleteMsg?.type === 'success' && <SuccessMessage message={deleteMsg.message} className="mb-4" />}
      {deleteMsg?.type === 'error' && <ErrorMessage message={deleteMsg.message} className="mb-4" />}

      {/* Stats strip */}
      {total > 0 && (
        <div className="flex flex-wrap gap-2 mb-5">
          {Object.entries(statusCounts).map(([s, count]) => (
            <button
              key={s}
              onClick={() => setStatusFilter(statusFilter === s ? '' : s)}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                statusFilter === s
                  ? 'bg-brand-600 text-white border-brand-600'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-brand-300'
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1).replace('_', ' ')}
              <span
                className={`rounded-full px-1.5 py-0.5 text-xs ${
                  statusFilter === s ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-500'
                }`}
              >
                {count}
              </span>
            </button>
          ))}
          {statusFilter && (
            <button
              onClick={() => setStatusFilter('')}
              className="text-xs text-slate-400 hover:text-slate-600 underline"
            >
              Clear filter
            </button>
          )}
        </div>
      )}

      {/* Count */}
      {!appsQ.isLoading && (
        <div className="text-sm text-slate-500 mb-4">
          {total} application{total !== 1 ? 's' : ''}{statusFilter ? ` · ${statusFilter}` : ''}
        </div>
      )}

      {appsQ.isLoading ? (
        <PageSpinner />
      ) : applications.length === 0 ? (
        <EmptyState
          icon="📋"
          title="No applications yet"
          description="Save a job to start tracking your applications here."
          action={
            <Link to="/jobs">
              <Button>Browse Jobs</Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-3">
          {applications.map((app) => (
            <ApplicationCard
              key={app.id}
              application={app}
              onUpdate={(id, patch) => updateMut.mutateAsync({ id, patch })}
              onDelete={(id) => deleteMut.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
