import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, List, Play, Database, Settings,
  MoreHorizontal, MessageSquare, Sliders, X, Target, Award, Activity,
} from 'lucide-react'

const mainTabs = [
  { to: '/', icon: LayoutDashboard, label: 'Home' },
  { to: '/instruments', icon: List, label: 'Instruments' },
  { to: '/run', icon: Play, label: 'Run' },
  { to: '/sources', icon: Database, label: 'Sources' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

const moreTabs = [
  { to: '/prompts', icon: MessageSquare, label: 'Prompts' },
  { to: '/digests', icon: Sliders, label: 'Digest Config' },
  { to: '/retrace', icon: Target, label: 'Retrace' },
  { to: '/scorecard', icon: Award, label: 'Score Cards' },
  { to: '/options', icon: Activity, label: 'Options Flow' },
]

export default function BottomNav() {
  const [showMore, setShowMore] = useState(false)

  return (
    <>
      {/* More popup */}
      {showMore && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={() => setShowMore(false)}>
          <div
            className="absolute bottom-[4.5rem] left-4 right-4 bg-white rounded-2xl shadow-xl border border-apple-gray-200 p-2"
            style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
            onClick={e => e.stopPropagation()}
          >
            {moreTabs.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setShowMore(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                    isActive ? 'bg-apple-blue/10 text-apple-blue' : 'text-apple-gray-600 active:bg-apple-gray-100'
                  }`
                }
              >
                <Icon size={20} />
                {label}
              </NavLink>
            ))}
          </div>
        </div>
      )}

      {/* Bottom tab bar */}
      <nav
        className="fixed bottom-0 inset-x-0 z-50 md:hidden bg-white/80 backdrop-blur-lg border-t border-apple-gray-200"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        <div className="flex items-center justify-around h-16">
          {mainTabs.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex flex-col items-center gap-0.5 px-2 py-1 min-w-[3.5rem] transition-colors ${
                  isActive ? 'text-apple-blue' : 'text-apple-gray-400 active:text-apple-gray-600'
                }`
              }
            >
              <Icon size={20} />
              <span className="text-[10px] font-medium">{label}</span>
            </NavLink>
          ))}
          <button
            onClick={() => setShowMore(!showMore)}
            className={`flex flex-col items-center gap-0.5 px-2 py-1 min-w-[3.5rem] transition-colors ${
              showMore ? 'text-apple-blue' : 'text-apple-gray-400 active:text-apple-gray-600'
            }`}
          >
            {showMore ? <X size={20} /> : <MoreHorizontal size={20} />}
            <span className="text-[10px] font-medium">More</span>
          </button>
        </div>
      </nav>
    </>
  )
}
