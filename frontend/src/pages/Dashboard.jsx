import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { FileText, Briefcase, BookmarkCheck, Zap, ArrowRight, ChevronRight } from 'lucide-react'
import { listResumes } from '../api/resumes'
import { listJobs } from '../api/jobs'
import { listApplications } from '../api/applications'
import { listWorkflows } from '../api/workflows'
import { Card } from '../components/ui/Card'
import { SourceBadge, StatusBadge } from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'
import Button from '../components/ui/Button'

function MetricCard({ icon: Icon, label, value, bgColor, iconColor, linkTo }) {
  const inner = (
    <Card className="flex items-center gap-4 hover:-translate-y-0.5 transition-transform duration-150">
      <div
        className="h-12 w-12 rounded-2xl flex items-center justify-center flex-shrink-0"
        style={{ backgroundColor: bgColor + '1a' }}
      >
        <Icon className="h-5 w-5" style={{ color: iconColor }} />
      </div>
      <div>
        <div className="text-2xl font-bold" style={{ color: '#334155', fontFamily: 'Poppins, sans-serif' }}>
          {value}
        </div>
        <div className="text-sm text-slate-400 font-medium">{label}</div>
      </div>
    </Card>
  )
  if (linkTo) return <Link to={linkTo}>{inner}</Link>
  return inner
}

function StepGuide({ resumes, jobs, applications }) {
  const steps = [
    { num: '1', label: 'Upload your resume', done: resumes.length > 0, to: '/resume' },
    { num: '2', label: 'Import jobs from a source', done: jobs.length > 0, to: '/find-jobs' },
    { num: '3', label: 'Save jobs you want to track', done: applications.length > 0, to: '/jobs' },
    {
      num: '4',
      label: 'Follow up on applications',
      done: applications.some((a) => a.status === 'applied'),
      to: '/applications',
    },
  ]

  return (
    <Card>
      <h3 className="text-base font-semibold text-slate-800 mb-4">Getting Started</h3>
      <div className="space-y-1.5">
        {steps.map((step) => (
          <Link
            key={step.num}
            to={step.to}
            className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 transition-colors group"
          >
            <div
              className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors ${
                step.done
                  ? 'bg-emerald-500 text-white'
                  : 'bg-brand-100 text-brand-500 group-hover:bg-brand-500 group-hover:text-white'
              }`}
            >
              {step.done ? '✓' : step.num}
            </div>
            <span className={`text-sm flex-1 font-medium ${step.done ? 'text-slate-400 line-through' : 'text-slate-700'}`}>
              {step.label}
            </span>
            <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-brand-500 transition-colors" />
          </Link>
        ))}
      </div>
    </Card>
  )
}

function NextAction({ resumes, jobs, applications }) {
  let message, to, cta

  if (!resumes.length) {
    message = 'Start by uploading your resume so we can match you to the right jobs.'
    to = '/resume'
    cta = 'Upload Resume'
  } else if (!jobs.length) {
    message = 'Great! Your resume is ready. Import jobs from your favourite sources.'
    to = '/find-jobs'
    cta = 'Find Jobs'
  } else if (!applications.length) {
    message = 'Jobs are in. Browse your matches and save the ones worth applying for.'
    to = '/jobs'
    cta = 'Review Matches'
  } else {
    message = 'Keep reviewing new jobs and tracking your application progress.'
    to = '/applications'
    cta = 'View Applications'
  }

  return (
    <div
      className="rounded-2xl p-5 text-white flex items-center justify-between gap-4"
      style={{ background: 'linear-gradient(135deg, #6366F1 0%, #4338ca 100%)', boxShadow: '0 10px 30px -10px rgba(99,102,241,0.4)' }}
    >
      <div>
        <div className="text-xs font-semibold text-white/60 uppercase tracking-widest mb-1">
          Your next step
        </div>
        <p className="text-sm text-white/90 font-medium">{message}</p>
      </div>
      <Link to={to} className="flex-shrink-0">
        <button
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold bg-white/20 hover:bg-white/30 text-white border border-white/30 transition-all duration-150 hover:-translate-y-0.5 active:translate-y-0"
        >
          {cta}
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </Link>
    </div>
  )
}

function RecentJobCard({ job }) {
  return (
    <div className="flex items-start justify-between py-3 border-b border-slate-100 last:border-0 gap-4">
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-slate-700 truncate">{job.title}</div>
        <div className="flex items-center gap-2 mt-1">
          <SourceBadge source={job.source} />
          {job.location && (
            <span className="text-xs text-slate-400 truncate">{job.location}</span>
          )}
        </div>
      </div>
      <StatusBadge status={job.status} />
    </div>
  )
}

export default function Dashboard() {
  const resumesQ = useQuery({ queryKey: ['resumes'], queryFn: () => listResumes(5, 0) })
  const jobsQ = useQuery({ queryKey: ['jobs', 'dashboard'], queryFn: () => listJobs({ limit: 5 }) })
  const appsQ = useQuery({
    queryKey: ['applications', 'dashboard'],
    queryFn: () => listApplications({ limit: 50 }),
  })
  const workflowsQ = useQuery({
    queryKey: ['workflows', 'dashboard'],
    queryFn: () => listWorkflows({ limit: 5 }),
  })

  const resumes = resumesQ.data?.items ?? []
  const jobs = jobsQ.data?.items ?? []
  const applications = appsQ.data?.items ?? []
  const savedCount = applications.filter((a) => a.status === 'saved').length
  const workflowCount = workflowsQ.data?.total ?? 0

  const isLoading = resumesQ.isLoading && jobsQ.isLoading

  if (isLoading) return <PageSpinner />

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
        <p className="text-slate-400 mt-1 font-medium">Your AI-powered job search workspace</p>
      </div>

      {/* Next action banner */}
      <div className="mb-6">
        <NextAction resumes={resumes} jobs={jobs} applications={applications} />
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricCard
          icon={FileText}
          label="Resumes"
          value={resumesQ.data?.total ?? 0}
          bgColor="#6366F1"
          iconColor="#6366F1"
          linkTo="/resume"
        />
        <MetricCard
          icon={Briefcase}
          label="Jobs Found"
          value={jobsQ.data?.total ?? 0}
          bgColor="#8b5cf6"
          iconColor="#8b5cf6"
          linkTo="/jobs"
        />
        <MetricCard
          icon={BookmarkCheck}
          label="Saved"
          value={savedCount}
          bgColor="#22C55E"
          iconColor="#22C55E"
          linkTo="/applications"
        />
        <MetricCard
          icon={Zap}
          label="AI Runs"
          value={workflowCount}
          bgColor="#f59e0b"
          iconColor="#f59e0b"
          linkTo="/find-jobs"
        />
      </div>

      {/* Two column: steps + recent jobs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StepGuide resumes={resumes} jobs={jobs} applications={applications} />

        <Card>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-base font-semibold text-slate-800">Recent Jobs</h3>
            <Link
              to="/jobs"
              className="text-xs text-brand-500 hover:text-brand-600 font-semibold flex items-center gap-1 transition-colors"
            >
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          {jobs.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-3xl mb-2">🔍</div>
              <p className="text-sm text-slate-400 font-medium">No jobs yet.</p>
              <Link to="/find-jobs" className="text-xs text-brand-500 hover:underline mt-1 inline-block font-semibold">
                Import from a source →
              </Link>
            </div>
          ) : (
            <div>
              {jobs.slice(0, 5).map((job) => (
                <RecentJobCard key={job.id} job={job} />
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
