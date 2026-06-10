import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BookmarkCheck,
  Briefcase,
  Check,
  ChevronRight,
  FileText,
  ListChecks,
  Radar,
  Search,
  Zap,
} from 'lucide-react'
import { listResumes } from '../api/resumes'
import { listJobs } from '../api/jobs'
import { listApplications } from '../api/applications'
import { listWorkflows } from '../api/workflows'
import { Card } from '../components/ui/Card'
import { SourceBadge, StatusBadge } from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'
import Button from '../components/ui/Button'

function MetricCard({ icon: Icon, label, value, accent, linkTo }) {
  const inner = (
    <Card
      accent={accent}
      className="group h-full transition-all duration-150 hover:-translate-y-1 hover:shadow-[8px_8px_0_rgba(24,33,47,0.10)]"
    >
      <div className="flex items-start justify-between gap-4">
        <div
          className="grid h-11 w-11 place-items-center rounded-lg border border-ink/10 text-ink"
          style={{ backgroundColor: accent }}
        >
          <Icon className="h-5 w-5" />
        </div>
        {linkTo && (
          <ArrowRight className="mt-1 h-4 w-4 text-muted transition-transform group-hover:translate-x-1 group-hover:text-ink" />
        )}
      </div>
      <div className="mt-5 font-display text-3xl font-bold leading-none text-ink">{value}</div>
      <div className="mt-1 text-sm font-bold text-muted">{label}</div>
    </Card>
  )

  if (linkTo) return <Link to={linkTo}>{inner}</Link>
  return inner
}

function StepGuide({ resumes, jobs, applications }) {
  const steps = [
    { num: '1', label: 'Resume uploaded', done: resumes.length > 0, to: '/resume', icon: FileText },
    { num: '2', label: 'Jobs imported', done: jobs.length > 0, to: '/find-jobs', icon: Search },
    { num: '3', label: 'Matches saved', done: applications.length > 0, to: '/jobs', icon: BookmarkCheck },
    {
      num: '4',
      label: 'Applications moving',
      done: applications.some((a) => a.status === 'applied'),
      to: '/applications',
      icon: ListChecks,
    },
  ]

  return (
    <Card accent="var(--sky)" className="h-full">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-muted">Track</p>
          <h2 className="font-display text-xl font-bold text-ink">Search loop</h2>
        </div>
        <div className="grid h-10 w-10 place-items-center rounded-lg bg-sky/20 text-ink">
          <Radar className="h-5 w-5" />
        </div>
      </div>

      <div className="space-y-2">
        {steps.map((step) => (
          <Link
            key={step.num}
            to={step.to}
            className="group flex items-center gap-3 rounded-lg border border-transparent px-3 py-3 transition-all hover:-translate-y-0.5 hover:border-ink/10 hover:bg-white"
          >
            <div
              className={`grid h-9 w-9 flex-shrink-0 place-items-center rounded-lg border text-sm font-extrabold ${
                step.done ? 'border-brand-500 bg-brand-100 text-brand-800' : 'border-ink/10 bg-white text-muted'
              }`}
            >
              {step.done ? <Check className="h-4 w-4" /> : step.num}
            </div>
            <div className="flex-1">
              <div className={`text-sm font-bold ${step.done ? 'text-ink' : 'text-muted'}`}>{step.label}</div>
              <div className="text-xs font-medium text-muted">
                {step.done ? 'Ready' : 'Open task'}
              </div>
            </div>
            <step.icon className="h-4 w-4 text-muted" />
            <ChevronRight className="h-4 w-4 text-muted transition-transform group-hover:translate-x-1 group-hover:text-ink" />
          </Link>
        ))}
      </div>
    </Card>
  )
}

function NextAction({ resumes, jobs, applications }) {
  let message, to, cta, Icon

  if (!resumes.length) {
    message = 'Upload your resume to turn it into a matching profile.'
    to = '/resume'
    cta = 'Upload resume'
    Icon = FileText
  } else if (!jobs.length) {
    message = 'Bring in fresh openings from ATS job boards.'
    to = '/find-jobs'
    cta = 'Find jobs'
    Icon = Search
  } else if (!applications.length) {
    message = 'Review your scored matches and save the strongest leads.'
    to = '/jobs'
    cta = 'Review matches'
    Icon = Briefcase
  } else {
    message = 'Keep your pipeline tidy and follow up at the right time.'
    to = '/applications'
    cta = 'Open pipeline'
    Icon = BookmarkCheck
  }

  return (
    <section className="relative overflow-hidden rounded-lg border border-ink bg-ink p-5 text-white shadow-[8px_8px_0_rgba(247,201,72,0.45)]">
      <div className="absolute bottom-0 left-0 h-2 w-1/3 bg-mint" />
      <div className="absolute bottom-0 left-1/3 h-2 w-1/3 bg-sun" />
      <div className="absolute bottom-0 right-0 h-2 w-1/3 bg-coral" />

      <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="grid h-12 w-12 flex-shrink-0 place-items-center rounded-lg bg-white text-ink">
            <Icon className="h-6 w-6" />
          </div>
          <div>
            <p className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-white/55">Next move</p>
            <p className="mt-1 max-w-xl font-display text-2xl font-bold leading-tight text-balance">{message}</p>
          </div>
        </div>
        <Link to={to} className="flex-shrink-0">
          <Button variant="sun">
            {cta}
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </div>
    </section>
  )
}

function RecentJobCard({ job }) {
  return (
    <div className="grid gap-3 border-b border-ink/10 py-4 last:border-0 sm:grid-cols-[1fr_auto] sm:items-start">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-lg bg-mint/20 text-xs font-extrabold text-brand-800">
            {(job.company_name || job.title || '?').charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-bold text-ink">{job.title}</div>
            <div className="truncate text-xs font-semibold text-muted">{job.company_name || 'Company not listed'}</div>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <SourceBadge source={job.source} />
          {job.location && <span className="text-xs font-semibold text-muted">{job.location}</span>}
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

  const isLoading = resumesQ.isLoading || jobsQ.isLoading || appsQ.isLoading

  if (isLoading) return <PageSpinner />

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-muted">Workspace</p>
          <h1 className="mt-1 font-display text-4xl font-bold leading-tight text-ink">Job search desk</h1>
        </div>
        <div className="rounded-lg border border-ink/10 bg-white px-4 py-3 text-sm font-semibold text-muted">
          <span className="font-bold text-ink">{jobsQ.data?.total ?? 0}</span> openings on the radar
        </div>
      </header>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(340px,0.65fr)]">
        <div className="space-y-5">
          <NextAction resumes={resumes} jobs={jobs} applications={applications} />

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard icon={FileText} label="Resumes" value={resumesQ.data?.total ?? 0} accent="#f7c948" linkTo="/resume" />
            <MetricCard icon={Briefcase} label="Jobs found" value={jobsQ.data?.total ?? 0} accent="#67b7f7" linkTo="/jobs" />
            <MetricCard icon={BookmarkCheck} label="Saved" value={savedCount} accent="#53d0a2" linkTo="/applications" />
            <MetricCard icon={Zap} label="Runs" value={workflowCount} accent="#f97066" linkTo="/find-jobs" />
          </div>
        </div>

        <StepGuide resumes={resumes} jobs={jobs} applications={applications} />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_0.55fr]">
        <Card accent="var(--plum)">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-muted">Latest</p>
              <h2 className="font-display text-xl font-bold text-ink">Recent jobs</h2>
            </div>
            <Link to="/jobs" className="text-sm font-bold text-ink hover:underline">
              View all
            </Link>
          </div>
          {jobs.length === 0 ? (
            <div className="rounded-lg border border-dashed border-ink/15 bg-white/70 px-5 py-8 text-center">
              <Search className="mx-auto h-7 w-7 text-muted" />
              <p className="mt-2 text-sm font-bold text-muted">No jobs imported yet.</p>
              <Link to="/find-jobs" className="mt-3 inline-flex">
                <Button size="sm">Start a search</Button>
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

        <Card accent="var(--sun)" className="bg-white">
          <p className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-muted">Rhythm</p>
          <h2 className="mt-1 font-display text-xl font-bold text-ink">A cleaner pipeline wins</h2>
          <p className="mt-3 text-sm font-medium leading-6 text-muted">
            Score imported jobs, save the strongest ones, then keep notes current as each application changes state.
          </p>
          <Link to="/applications" className="mt-5 inline-flex">
            <Button variant="secondary" size="sm">
              Open applications
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </Card>
      </div>
    </div>
  )
}
