/**
 * Workout History Page
 * Lists all past workout sessions
 */
import { useState, useEffect } from 'react'
import { workoutApi, type WorkoutSession } from '../services/workouts'
import WorkoutCard from '../components/history/WorkoutCard'
import WorkoutDetail from '../components/history/WorkoutDetail'

export default function WorkoutHistory() {
  const [workouts, setWorkouts] = useState<WorkoutSession[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedWorkout, setSelectedWorkout] = useState<WorkoutSession | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadWorkouts()
  }, [])

  const loadWorkouts = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await workoutApi.list({ limit: 100 })
      setWorkouts(response.workouts)
    } catch (err) {
      console.error('Failed to load workout history:', err)
      setError('Failed to load workout history. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading workout history...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
            <button
              onClick={loadWorkouts}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Workout History</h1>
          <p className="text-gray-600">
            View and analyze your past workout sessions
          </p>
        </div>

        {workouts.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <p className="text-gray-500 text-lg">No workout history yet.</p>
            <p className="text-gray-400 mt-2">Complete your first workout to see it here!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {workouts.map((workout) => (
              <WorkoutCard
                key={workout.id}
                workout={workout}
                onClick={() => setSelectedWorkout(workout)}
              />
            ))}
          </div>
        )}

        {/* Workout Detail Modal */}
        {selectedWorkout && (
          <WorkoutDetail
            workout={selectedWorkout}
            onClose={() => setSelectedWorkout(null)}
          />
        )}
      </div>
    </div>
  )
}
