/**
 * Last Workout Option Component
 * Shows option to copy exercises from the last completed workout
 */
import { workoutApi, type WorkoutSession } from '../../services/workouts'
import { formatDistanceToNow } from 'date-fns'

interface LastWorkoutOptionProps {
  lastWorkout: WorkoutSession
  onCopy: () => void
  loading?: boolean
}

export default function LastWorkoutOption({
  lastWorkout,
  onCopy,
  loading,
}: LastWorkoutOptionProps) {
  const completedDate = lastWorkout.completed_at
    ? new Date(lastWorkout.completed_at)
    : null

  const timeAgo = completedDate
    ? formatDistanceToNow(completedDate, { addSuffix: true })
    : 'Unknown'

  const exerciseCount = lastWorkout.exercises.length

  return (
    <div className="border rounded-lg p-4 bg-gray-50">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="font-semibold text-gray-900">
            Copy from Last Workout
          </div>
          <div className="text-sm text-gray-600 mt-1">
            Completed {timeAgo}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {exerciseCount} exercise{exerciseCount !== 1 ? 's' : ''} performed
          </div>
        </div>
      </div>
      
      <button
        onClick={onCopy}
        disabled={loading}
        className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm"
      >
        {loading ? 'Loading...' : 'Copy Last Workout Exercises'}
      </button>
    </div>
  )
}
