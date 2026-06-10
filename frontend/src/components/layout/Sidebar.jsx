import { NavLink } from 'react-router-dom'
import {
  Briefcase,
  ClipboardList,
  FileText,
  LayoutDashboard,
  Radar,
  Search,
  Settings,
} from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true, accent: 'bg-sun' },
  { to: '/resume', icon: FileText, label: 'Resume', accent: 'bg-mint' },
  { to: '/find-jobs', icon: Search, label: 'Find Jobs', accent: 'bg-sky' },
  { to: '/jobs', icon: Briefcase, label: 'Matches', accent: 'bg-plum' },
  { to: '/applications', icon: ClipboardList, label: 'Applications', accent: 'bg-coral' },
  { to: '/settings', icon: Settings, label: 'Settings', accent: 'bg-ink' },
]

export default function Sidebar() {
  return (
    <aside className="fixed inset-x-0 top-0 z-40 border-b border-ink/10 bg-paper/90 shadow-[0_10px_35px_rgba(24,33,47,0.08)] backdrop-blur-xl lg:inset-y-0 lg:left-0 lg:w-72 lg:border-b-0 lg:border-r">
      <div className="flex h-full flex-col gap-3 p-3 lg:p-5">
        <div className="flex items-center justify-between gap-3 rounded-lg border border-ink/10 bg-white px-3 py-3 shadow-[4px_4px_0_rgba(83,208,162,0.22)]">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-lg border border-ink/10 bg-sun text-ink">
              <Radar className="h-5 w-5" />
            </div>
            <div>
              <div className="font-display text-base font-bold leading-tight text-ink">CareerFit</div>
              <div className="text-xs font-bold uppercase tracking-[0.18em] text-muted">Radar</div>
            </div>
          </div>
          <span className="hidden rounded-md bg-mint/20 px-2 py-1 text-[10px] font-extrabold uppercase tracking-[0.16em] text-brand-800 sm:inline-flex lg:hidden">
            Hunt
          </span>
        </div>

        <nav className="scrollbar-thin flex gap-2 overflow-x-auto pb-1 lg:mt-4 lg:flex-col lg:overflow-visible lg:pb-0">
          {navItems.map(({ to, icon: Icon, label, end, accent }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `group relative flex min-w-fit items-center gap-2.5 rounded-lg border px-3 py-2.5 text-sm font-bold transition-all duration-150 lg:min-w-0 ${
                  isActive
                    ? 'border-ink bg-ink text-white shadow-[4px_4px_0_rgba(83,208,162,0.45)]'
                    : 'border-transparent text-muted hover:-translate-y-0.5 hover:border-ink/10 hover:bg-white hover:text-ink hover:shadow-[3px_3px_0_rgba(24,33,47,0.10)]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span className={`h-2.5 w-2.5 rounded-[3px] ${accent} ${isActive ? 'opacity-100' : 'opacity-70'}`} />
                  <Icon className="h-4 w-4 flex-shrink-0" />
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto hidden rounded-lg border border-ink/10 bg-white px-4 py-4 lg:block">
          <div className="mb-2 h-1.5 w-12 rounded-full bg-coral" />
          <p className="text-sm font-bold text-ink">Job search, kept tidy.</p>
          <p className="mt-1 text-xs font-medium leading-5 text-muted">
            Import, score, save, and track without losing the thread.
          </p>
        </div>
      </div>
    </aside>
  )
}
