import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import DayPlans from './pages/DayPlans'
import Session from './pages/Session'
import ExerciseBrowser from './pages/ExerciseBrowser'
import Settings from './pages/Settings'
import WorkoutHistory from './pages/WorkoutHistory'
import Analytics from './pages/Analytics'
import PersonalRecords from './pages/PersonalRecords'
import ResumeBanner from './components/session/ResumeBanner'
import { useUserStore } from './stores/userStore'

/**
 * Seven destinations do not fit a phone: at 390px the inline bar measured
 * 525px wide, pushing Records and Settings off-screen and giving every page a
 * horizontal scroll. Below `sm` they collapse behind a toggle instead.
 */
const NAV_LINKS: { to: string; label: string }[] = [
  { to: '/', label: 'Day Plans' },
  { to: '/session', label: 'Session' },
  { to: '/exercises', label: 'Exercise Browser' },
  { to: '/history', label: 'History' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/records', label: 'Records' },
  { to: '/settings', label: 'Settings' },
]

function App() {
  const { fetchCurrentUser } = useUserStore()
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    // Fetch/create user on app load
    fetchCurrentUser()
  }, [fetchCurrentUser])

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm border-b">
          <div className="container mx-auto px-6 py-4">
            <div className="flex flex-wrap justify-between items-center">
              <Link
                to="/"
                className="text-2xl font-bold text-blue-600 hover:text-blue-700"
                onClick={() => setMenuOpen(false)}
              >
                SlotFit
              </Link>
              <button
                onClick={() => setMenuOpen((open) => !open)}
                className="sm:hidden p-2 -mr-2 min-h-[44px] min-w-[44px] text-gray-700"
                aria-label="Toggle navigation"
                aria-expanded={menuOpen}
              >
                <span aria-hidden="true">{menuOpen ? '✕' : '☰'}</span>
              </button>
              <div
                className={`${
                  menuOpen ? 'flex' : 'hidden'
                } flex-col gap-1 w-full pt-2 sm:flex sm:flex-row sm:items-center sm:gap-4 sm:w-auto sm:pt-0`}
              >
                {NAV_LINKS.map((link) => (
                  <Link
                    key={link.to}
                    to={link.to}
                    onClick={() => setMenuOpen(false)}
                    className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </nav>

        <ResumeBanner />

        <Routes>
          <Route path="/" element={<DayPlans />} />
          <Route path="/session" element={<Session />} />
          <Route path="/exercises" element={<ExerciseBrowser />} />
          <Route path="/history" element={<WorkoutHistory />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/records" element={<PersonalRecords />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
