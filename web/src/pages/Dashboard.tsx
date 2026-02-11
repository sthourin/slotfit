/**
 * Personal Dashboard
 * Quick access to workout history and new workout flow
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { workoutApi, type WorkoutSession } from '../services/workouts'
import { recommendationApi, type NextWorkoutSuggestion } from '../services/recommendations'
import { useWorkoutStore } from '../stores/workoutStore'
import WorkoutCard from '../components/history/WorkoutCard'
import WorkoutDetail from '../components/history/WorkoutDetail'
import WorkoutSummary from '../components/workout/WorkoutSummary'

export default function Dashboard() {
  const navigate = useNavigate()
  const { loadWorkout } = useWorkoutStore()
  const [workouts, setWorkouts] = useState<WorkoutSession[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedWorkout, setSelectedWorkout] = useState<WorkoutSession | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastCompletedWorkout, setLastCompletedWorkout] = useState<WorkoutSession | null>(null)
  const [suggestion, setSuggestion] = useState<NextWorkoutSuggestion | null>(null)
  const [suggestionLoading, setSuggestionLoading] = useState(false)
  const [suggestionError, setSuggestionError] = useState<string | null>(null)
  const [plannedSessions, setPlannedSessions] = useState<number | undefined>(undefined)
  const [startingWorkout, setStartingWorkout] = useState(false)

  useEffect(() => {
    loadWorkouts()
    loadSuggestion()
  }, [])

  const loadWorkouts = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await workoutApi.list({ limit: 12 })
      setWorkouts(response.workouts)
      const lastCompleted = response.workouts.find((workout) => workout.state === 'completed')
      setLastCompletedWorkout(lastCompleted || null)
    } catch (err) {
      console.error('Failed to load workout history:', err)
      setError('Failed to load workout history. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const loadSuggestion = async (sessions?: number) => {
    setSuggestionLoading(true)
    setSuggestionError(null)
    try {
      const response = await recommendationApi.getNextWorkoutSuggestion(sessions ?? plannedSessions)
      setSuggestion(response)
    } catch (err) {
      console.error('Failed to load next workout suggestion:', err)
      setSuggestionError('Failed to load suggestion.')
    } finally {
      setSuggestionLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-6xl space-y-6">
        <div className="bg-white rounded-lg shadow-sm p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Your Dashboard</h1>
            <p className="text-gray-600 mt-2">
              Review recent workouts and jump into your next session.
            </p>
          </div>
          <button
            onClick={() =>
              suggestion?.suggested_routine_id
                ? navigate(`/workout/start?routineId=${suggestion.suggested_routine_id}`)
                : navigate('/workout/start')
            }
            className="px-5 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Start New Workout
          </button>
        </div>

        {lastCompletedWorkout && (
          <WorkoutSummary workout={lastCompletedWorkout} variant="inline" />
        )}

        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Next Workout Suggestion</h2>
            <button
              onClick={() => loadSuggestion()}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Refresh
            </button>
          </div>

          <div className="flex items-center gap-3 mb-4">
            <label className="text-sm text-gray-600">Sessions this week:</label>
            <select
              value={plannedSessions ?? ''}
              onChange={(e) => {
                const val = e.target.value ? Number(e.target.value) : undefined
                setPlannedSessions(val)
                loadSuggestion(val)
              }}
              className="border border-gray-300 rounded-md px-2 py-1 text-sm"
            >
              <option value="">Auto (from history)</option>
              {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                <option key={n} value={n}>{n} session{n > 1 ? 's' : ''}</option>
              ))}
            </select>
          </div>

          {suggestionLoading ? (
            <div className="text-center py-6">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-3 text-gray-600">Generating suggestion...</p>
            </div>
          ) : suggestionError ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800">{suggestionError}</p>
            </div>
          ) : suggestion ? (
            <div className="space-y-3">
              <div>
                <div className="text-sm text-gray-500">Suggested routine</div>
                <div className="text-lg font-semibold">
                  {suggestion.suggested_routine_name || 'Choose a routine'}
                </div>
              </div>
              {suggestion.focus && (
                <div>
                  <div className="text-sm text-gray-500">Focus</div>
                  <div className="text-gray-800">{suggestion.focus}</div>
                </div>
              )}
              <div>
                <div className="text-sm text-gray-500">Why</div>
                <div className="text-gray-700">{suggestion.rationale}</div>
              </div>
              {suggestion.suggested_exercises.length > 0 && (
                <div>
                  <div className="text-sm text-gray-500">Suggested exercises</div>
                  <div className="text-gray-700">
                    {suggestion.suggested_exercises.join(', ')}
                  </div>
                </div>
              )}
              {(suggestion.provider || suggestion.model) && (
                <div className="text-xs text-gray-400">
                  {suggestion.provider && <span>Provider: {suggestion.provider}</span>}
                  {suggestion.provider && suggestion.model && <span> &middot; </span>}
                  {suggestion.model && <span>Model: {suggestion.model}</span>}
                </div>
              )}
              {suggestion.prompt && (
                <details className="text-xs">
                  <summary className="text-gray-400 cursor-pointer hover:text-gray-600">
                    View prompt
                  </summary>
                  <pre className="mt-2 p-3 bg-gray-50 rounded border text-gray-600 whitespace-pre-wrap overflow-x-auto max-h-64 overflow-y-auto">
                    {suggestion.prompt}
                  </pre>
                </details>
              )}
              {suggestion.suggested_routine_id && suggestion.suggested_exercises.length > 0 && (
                <button
                  disabled={startingWorkout}
                  onClick={async () => {
                    setStartingWorkout(true)
                    try {
                      const workout = await workoutApi.startFromSuggestion({
                        routine_id: suggestion.suggested_routine_id!,
                        exercise_names: suggestion.suggested_exercises,
                      })
                      await loadWorkout(workout.id)
                      navigate('/workout')
                    } catch (err) {
                      console.error('Failed to start suggested workout:', err)
                      setSuggestionError('Failed to start workout. Please try again.')
                    } finally {
                      setStartingWorkout(false)
                    }
                  }}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition-colors"
                >
                  {startingWorkout ? 'Starting...' : 'Start Suggested Workout'}
                </button>
              )}
            </div>
          ) : (
            <div className="text-gray-500">No suggestion available.</div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Recent Workouts</h2>
            <button
              onClick={() => navigate('/history')}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              View all
            </button>
          </div>

          {loading ? (
            <div className="text-center py-10">
              <div className="inline-block animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
              <p className="mt-4 text-gray-600">Loading workout history...</p>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800">{error}</p>
              <button
                onClick={loadWorkouts}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : workouts.length === 0 ? (
            <div className="text-center py-10 text-gray-500">
              <p>No workout history yet.</p>
              <p className="text-sm text-gray-400 mt-2">
                Complete your first workout to see it here.
              </p>
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
        </div>
      </div>

      {selectedWorkout && (
        <WorkoutDetail workout={selectedWorkout} onClose={() => setSelectedWorkout(null)} />
      )}
    </div>
  )
}
