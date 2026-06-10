import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  FileText,
  Search,
  Briefcase,
  ClipboardList,
  Settings,
} from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/resume', icon: FileText, label: 'My Resume' },
  { to: '/find-jobs', icon: Search, label: 'Find Jobs' },
  { to: '/jobs', icon: Briefcase, label: 'Job Matches' },
  { to: '/applications', icon: ClipboardList, label: 'Applications' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside
      className="fixed inset-y-0 left-0 w-56 flex flex-col z-40"
      style={{ background: 'linear-gradient(160deg, #4338ca 0%, #312e81 100%)' }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-white/10">
        <div className="h-8 w-8 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
          <span className="text-white text-sm font-bold">CF</span>
        </div>
        <div>
          <div className="text-white font-bold text-sm leading-tight" style={{ fontFamily: 'Poppins, sans-serif' }}>
            CareerFit
          </div>
          <div className="text-white/50 text-xs leading-tight">Radar</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        <div className="space-y-0.5">
          {navItems.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-150 ${
                  isActive
                    ? 'bg-white/20 text-white font-semibold shadow-sm'
                    : 'text-white/65 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Footer hint */}
      <div className="px-5 py-4 border-t border-white/10">
        <p className="text-white/40 text-xs">AI-powered job search</p>
      </div>
    </aside>
  )
}
