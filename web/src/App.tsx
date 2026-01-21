import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import RoutineDesigner from './pages/RoutineDesigner'
import ExerciseBrowser from './pages/ExerciseBrowser'
import Settings from './pages/Settings'
import WorkoutStart from './pages/WorkoutStart'
import Workout from './pages/Workout'
import WorkoutHistory from './pages/WorkoutHistory'
import Analytics from './pages/Analytics'
import PersonalRecords from './pages/PersonalRecords'
import { useUserStore } from './stores/userStore'

function App() {
  const { fetchCurrentUser } = useUserStore()

  useEffect(() => {
    // Fetch/create user on app load
    fetchCurrentUser()
  }, [fetchCurrentUser])

  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm border-b">
          <div className="container mx-auto px-6 py-4">
            <div className="flex justify-between items-center">
                <Link to="/" className="text-2xl font-bold text-blue-600 hover:text-blue-700">
                SlotFit
              </Link>
              <div className="space-x-4">
                <Link
                  to="/"
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Dashboard
                </Link>
                <Link
                  to="/routines"
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Routine Designer
                </Link>
                <Link
                  to="/workout/start"
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Start Workout
                </Link>
                <Link
                  to="/exercises"
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Exercise Browser
                </Link>
                <Link
                  to="/history"
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  History
                </Link>
                <Link
                  to="/analytics"
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Analytics
                </Link>
                <Link
                  to="/records"
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Records
                </Link>
                <Link
                  to="/settings"
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Settings
                </Link>
              </div>
            </div>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/routines" element={<RoutineDesigner />} />
          <Route path="/workout/start" element={<WorkoutStart />} />
          <Route path="/workout" element={<Workout />} />
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
