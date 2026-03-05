import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, List, MessageSquare, Database,
  Sliders, Play, Settings, Target, Award, Activity,
} from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/instruments', icon: List, label: 'Instruments' },
  { to: '/prompts', icon: MessageSquare, label: 'Prompts' },
  { to: '/sources', icon: Database, label: 'Data Sources' },
  { to: '/digests', icon: Sliders, label: 'Digest Config' },
  { to: '/run', icon: Play, label: 'Run & Preview' },
  { to: '/retrace', icon: Target, label: 'Retrace' },
  { to: '/scorecard', icon: Award, label: 'Score Cards' },
  { to: '/options', icon: Activity, label: 'Options Flow' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className="hidden md:flex w-56 bg-white border-r border-apple-gray-200 flex-col min-h-screen sticky top-0">
      <div className="p-5 border-b border-apple-gray-200">
        <h1 className="text-lg font-semibold text-apple-gray-800 tracking-tight">
          Market Digest
        </h1>
        <p className="text-xs text-apple-gray-400 mt-0.5">Command Center</p>
      </div>
      <nav className="flex-1 p-3 space-y-0.5">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-apple-blue text-white'
                  : 'text-apple-gray-600 hover:bg-apple-gray-100'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
