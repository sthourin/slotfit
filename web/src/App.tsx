import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import RoutineDesigner from './pages/RoutineDesigner'
import ExerciseBrowser from './pages/ExerciseBrowser'

function App() {
  return (
    <BrowserRouter>
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
                  Routine Designer
                </Link>
                <Link
                  to="/exercises"
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Exercise Browser
                </Link>
              </div>
            </div>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={<RoutineDesigner />} />
          <Route path="/exercises" element={<ExerciseBrowser />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
