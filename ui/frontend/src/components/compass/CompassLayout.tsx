// Compass standalone shell — a calm, focused app for a long-term investor.
// No trading terminals, no jargon: its own header, nav, and bottom tabs.
import { useEffect, useState } from 'react'
import { NavLink, Outlet, Link } from 'react-router-dom'
import {
  Home, Compass, Sparkles, MessageCircleQuestion, MoreHorizontal, X,
  Eye, PiggyBank, ArrowLeftRight, GraduationCap, TerminalSquare,
} from 'lucide-react'

interface Tab {
  to: string
  icon: typeof Home
  label: string
  end?: boolean
}

const mainTabs: Tab[] = [
  { to: '/compass', icon: Home, label: 'Home', end: true },
  { to: '/compass/portfolio', icon: Compass, label: 'Portfolio' },
  { to: '/compass/ideas', icon: Sparkles, label: 'Ideas' },
  { to: '/compass/ask', icon: MessageCircleQuestion, label: 'Ask' },
]

const moreTabs: Tab[] = [
  { to: '/compass/watchlist', icon: Eye, label: 'Watchlist' },
  { to: '/compass/retire', icon: PiggyBank, label: 'Retirement' },
  { to: '/compass/compare', icon: ArrowLeftRight, label: 'Compare' },
  { to: '/compass/learn', icon: GraduationCap, label: 'Learn' },
]

export default function CompassLayout() {
  const [showMore, setShowMore] = useState(false)

  // While inside Compass, the browser tab / home-screen identity is Compass:
  // its own title, icon, and PWA manifest (so "Add to Home Screen" installs
  // Compass at /compass, not the trading Command Center).
  useEffect(() => {
    const prevTitle = document.title
    document.title = 'Compass'

    const manifest = document.querySelector<HTMLLinkElement>('link[rel="manifest"]')
    const prevManifest = manifest?.href ?? null
    if (manifest) manifest.href = '/compass-manifest.json'

    const touchIcon = document.createElement('link')
    touchIcon.rel = 'apple-touch-icon'
    touchIcon.href = '/compass-icon-180.png'
    document.head.appendChild(touchIcon)

    return () => {
      document.title = prevTitle
      if (manifest && prevManifest) manifest.href = prevManifest
      touchIcon.remove()
    }
  }, [])

  return (
    <div className="min-h-screen bg-apple-gray-100">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-apple-gray-200 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4">
          <NavLink to="/compass" end className="flex items-center gap-2">
            <Compass size={20} className="text-apple-blue" />
            <span className="text-base font-bold tracking-tight text-apple-gray-800">Compass</span>
          </NavLink>
          {/* Desktop nav */}
          <nav className="hidden items-center gap-1 md:flex">
            {[...mainTabs, ...moreTabs].map(({ to, label, end }) => (
              <NavLink key={to} to={to} end={end}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive ? 'bg-apple-blue/10 text-apple-blue' : 'text-apple-gray-500 hover:bg-apple-gray-100'
                  }`}>
                {label}
              </NavLink>
            ))}
            <Link to="/" title="Back to Command Center"
              className="ml-2 flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-apple-gray-300 hover:text-apple-gray-500">
              <TerminalSquare size={14} />
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-4 pb-24 md:pb-8">
        <Outlet />
      </main>

      {/* Mobile more sheet */}
      {showMore && (
        <div className="fixed inset-0 z-40 bg-black/20 md:hidden" onClick={() => setShowMore(false)}>
          <div
            className="absolute bottom-[4.5rem] left-4 right-4 rounded-2xl border border-apple-gray-200 bg-white p-2 shadow-xl"
            style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
            onClick={e => e.stopPropagation()}
          >
            {moreTabs.map(({ to, icon: Icon, label }) => (
              <NavLink key={to} to={to} onClick={() => setShowMore(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium ${
                    isActive ? 'bg-apple-blue/10 text-apple-blue' : 'text-apple-gray-600 active:bg-apple-gray-100'
                  }`}>
                <Icon size={20} />
                {label}
              </NavLink>
            ))}
            <Link to="/" onClick={() => setShowMore(false)}
              className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium text-apple-gray-400 active:bg-apple-gray-100">
              <TerminalSquare size={20} />
              Command Center
            </Link>
          </div>
        </div>
      )}

      {/* Mobile bottom tabs */}
      <nav
        className="fixed inset-x-0 bottom-0 z-50 border-t border-apple-gray-200 bg-white/85 backdrop-blur-lg md:hidden"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        <div className="flex h-16 items-center justify-around">
          {mainTabs.map(({ to, icon: Icon, label, end }) => (
            <NavLink key={to} to={to} end={end}
              className={({ isActive }) =>
                `flex min-w-[3.5rem] flex-col items-center gap-0.5 px-2 py-1 transition-colors ${
                  isActive ? 'text-apple-blue' : 'text-apple-gray-400 active:text-apple-gray-600'
                }`}>
              <Icon size={20} />
              <span className="text-[10px] font-medium">{label}</span>
            </NavLink>
          ))}
          <button onClick={() => setShowMore(!showMore)}
            className={`flex min-w-[3.5rem] flex-col items-center gap-0.5 px-2 py-1 ${showMore ? 'text-apple-blue' : 'text-apple-gray-400'}`}>
            {showMore ? <X size={20} /> : <MoreHorizontal size={20} />}
            <span className="text-[10px] font-medium">More</span>
          </button>
        </div>
      </nav>
    </div>
  )
}
