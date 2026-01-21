/**
 * Workout Card Component
 * Displays a summary card for a workout session
 */
import { type WorkoutSession } from '../../services/workouts'
import { TagDisplay } from '../TagDisplay'

interface WorkoutCardProps {
  workout: WorkoutSession
  onClick: () => void
}

export default function WorkoutCard({ workout, onClick }: WorkoutCardProps) {
  // Calculate workout duration
  const duration = workout.started_at && workout.completed_at
    ? new Date(workout.completed_at).getTime() - new Date(workout.started_at).getTime()
    : 0

  const formatDuration = (ms: number) => {
    const minutes = Math.floor(ms / 60000)
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    if (hours > 0) {
      return `${hours}h ${mins}m`
    }
    return `${mins}m`
  }

  // Calculate total volume
  const totalVolume = workout.exercises.reduce((sum, exercise) => {
    return (
      sum +
      exercise.sets.reduce((setSum, set) => {
        const volume = (set.reps || 0) * (set.weight || 0)
        return setSum + volume
      }, 0)
    )
  }, 0)

  // Calculate total sets
  const totalSets = workout.exercises.reduce(
    (sum, exercise) => sum + exercise.sets.length,
    0
  )

  // Calculate completed slots
  const completedSlots = workout.exercises.filter(
    (e) => e.slot_state === 'completed'
  ).length

  const getStateColor = (state: string) => {
    switch (state) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'abandoned':
        return 'bg-red-100 text-red-800'
      case 'active':
        return 'bg-blue-100 text-blue-800'
      case 'paused':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow cursor-pointer border border-gray-200"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold">
              {workout.completed_at
                ? new Date(workout.completed_at).toLocaleDateString()
                : workout.started_at
                ? new Date(workout.started_at).toLocaleDateString()
                : 'Workout'}
            </h3>
            <span
              className={`px-2 py-1 text-xs font-medium rounded ${getStateColor(workout.state)}`}
            >
              {workout.state}
            </span>
          </div>
          {workout.completed_at && (
            <p className="text-sm text-gray-500">
              {new Date(workout.completed_at).toLocaleTimeString()}
            </p>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Duration:</span>
          <span className="font-medium">{formatDuration(duration)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Total Volume:</span>
          <span className="font-medium">{totalVolume.toLocaleString()} lbs</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Total Sets:</span>
          <span className="font-medium">{totalSets}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Exercises:</span>
          <span className="font-medium">
            {completedSlots}/{workout.exercises.length} completed
          </span>
        </div>
      </div>

      {/* Tags */}
      {workout.tags && workout.tags.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <TagDisplay tags={workout.tags} size="sm" />
        </div>
      )}
    </div>
  )
}
