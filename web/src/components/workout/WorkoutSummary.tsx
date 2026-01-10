/**
 * Workout Summary Component
 * Displays summary of completed workout
 */
import { type WorkoutSession, type WorkoutExercise } from '../../services/workouts'
import { exerciseApi, type Exercise } from '../../services/exercises'
import { useState, useEffect } from 'react'
import VolumeBreakdown from './VolumeBreakdown'
import PRNotification from './PRNotification'

interface WorkoutSummaryProps {
  workout: WorkoutSession
  onClose: () => void
}

export default function WorkoutSummary({ workout, onClose }: WorkoutSummaryProps) {
  const [exerciseDetails, setExerciseDetails] = useState<Map<number, Exercise>>(new Map())
  const [loading, setLoading] = useState(true)

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

  // Load exercise details
  useEffect(() => {
    const loadExercises = async () => {
      const exerciseIds = workout.exercises
        .map((e) => e.exercise_id)
        .filter((id): id is number => id !== null && id !== undefined)

      try {
        const exercises = await Promise.all(
          exerciseIds.map((id) => exerciseApi.get(id).catch(() => null))
        )
        const exerciseMap = new Map<number, Exercise>()
        exercises.forEach((ex, idx) => {
          if (ex) {
            exerciseMap.set(exerciseIds[idx], ex)
          }
        })
        setExerciseDetails(exerciseMap)
      } catch (error) {
        console.error('Failed to load exercise details:', error)
      } finally {
        setLoading(false)
      }
    }

    loadExercises()
  }, [workout.exercises])

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

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          className="relative bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b bg-green-50">
            <div>
              <h2 className="text-2xl font-bold text-green-800">Workout Complete! 🎉</h2>
              <p className="text-sm text-green-600 mt-1">
                Completed on {workout.completed_at ? new Date(workout.completed_at).toLocaleString() : 'N/A'}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="text-sm text-blue-600 font-medium">Duration</div>
                <div className="text-2xl font-bold text-blue-900 mt-1">
                  {formatDuration(duration)}
                </div>
              </div>
              <div className="bg-purple-50 rounded-lg p-4">
                <div className="text-sm text-purple-600 font-medium">Total Volume</div>
                <div className="text-2xl font-bold text-purple-900 mt-1">
                  {totalVolume.toLocaleString()} lbs
                </div>
              </div>
              <div className="bg-orange-50 rounded-lg p-4">
                <div className="text-sm text-orange-600 font-medium">Total Sets</div>
                <div className="text-2xl font-bold text-orange-900 mt-1">{totalSets}</div>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <div className="text-sm text-green-600 font-medium">Slots Completed</div>
                <div className="text-2xl font-bold text-green-900 mt-1">
                  {completedSlots}/{workout.exercises.length}
                </div>
              </div>
            </div>

            {/* PR Notifications */}
            <PRNotification workout={workout} exerciseDetails={exerciseDetails} />

            {/* Volume Breakdown */}
            <VolumeBreakdown workout={workout} exerciseDetails={exerciseDetails} />

            {/* Exercise Summary */}
            <div>
              <h3 className="text-lg font-semibold mb-3">Exercise Summary</h3>
              <div className="space-y-2">
                {workout.exercises.map((exercise) => {
                  const exerciseDetail = exerciseDetails.get(exercise.exercise_id)
                  const exerciseVolume = exercise.sets.reduce(
                    (sum, set) => sum + (set.reps || 0) * (set.weight || 0),
                    0
                  )

                  return (
                    <div
                      key={exercise.id}
                      className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-semibold">
                            {exerciseDetail?.name || `Exercise ${exercise.exercise_id}`}
                          </h4>
                          <div className="text-sm text-gray-600 mt-1">
                            {exercise.sets.length} set{exercise.sets.length !== 1 ? 's' : ''} •{' '}
                            {exerciseVolume.toLocaleString()} lbs total volume
                          </div>
                          <div className="mt-2 space-y-1">
                            {exercise.sets.map((set) => (
                              <div key={set.id} className="text-xs text-gray-500">
                                Set {set.set_number}: {set.reps || '—'} reps × {set.weight || '—'} lbs
                              </div>
                            ))}
                          </div>
                        </div>
                        <span
                          className={`px-2 py-1 text-xs rounded ${
                            exercise.slot_state === 'completed'
                              ? 'bg-green-100 text-green-800'
                              : exercise.slot_state === 'skipped'
                              ? 'bg-gray-100 text-gray-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {exercise.slot_state}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-6 border-t bg-gray-50">
            <div className="flex justify-end gap-3">
              <button
                onClick={onClose}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
