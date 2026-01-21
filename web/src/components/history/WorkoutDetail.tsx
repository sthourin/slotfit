/**
 * Workout Detail Component
 * Shows detailed information about a workout session
 */
import { type WorkoutSession } from '../../services/workouts'
import { exerciseApi, type Exercise } from '../../services/exercises'
import { useState, useEffect } from 'react'
import VolumeBreakdown from '../workout/VolumeBreakdown'
import { TagDisplay } from '../TagDisplay'
import { TagInput } from '../TagInput'
import { workoutApi } from '../../services/workouts'
import { tagsService, type Tag } from '../../services/tags'

interface WorkoutDetailProps {
  workout: WorkoutSession
  onClose: () => void
}

export default function WorkoutDetail({ workout, onClose }: WorkoutDetailProps) {
  const [exerciseDetails, setExerciseDetails] = useState<Map<number, Exercise>>(new Map())
  const [loading, setLoading] = useState(true)
  const [workoutTags, setWorkoutTags] = useState<Tag[]>(workout.tags || [])
  const [savingTags, setSavingTags] = useState(false)
  const [editingTags, setEditingTags] = useState(false)

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

  // Sync tags when workout changes
  useEffect(() => {
    setWorkoutTags(workout.tags || [])
  }, [workout.tags])

  const handleTagsChange = async (newTags: Tag[]) => {
    if (!workout.id) return

    setSavingTags(true)
    try {
      const currentTagIds = new Set(workoutTags.map((t) => t.id))
      const newTagIds = new Set(newTags.map((t) => t.id))

      // Find tags to add
      const tagsToAdd = newTags.filter((tag) => !currentTagIds.has(tag.id))
      // Find tags to remove
      const tagsToRemove = workoutTags.filter((tag) => !newTagIds.has(tag.id))

      // Add new tags
      for (const tag of tagsToAdd) {
        await workoutApi.addTag(workout.id, tag.name)
      }

      // Remove old tags
      for (const tag of tagsToRemove) {
        await workoutApi.removeTag(workout.id, tag.id)
      }

      // Reload workout to get updated tags
      const updated = await workoutApi.get(workout.id)
      setWorkoutTags(updated.tags || [])
    } catch (error) {
      console.error('Failed to update tags:', error)
      alert('Failed to update tags. Please try again.')
    } finally {
      setSavingTags(false)
    }
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
          className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b">
            <div>
              <h2 className="text-2xl font-bold">Workout Details</h2>
              <p className="text-sm text-gray-600 mt-1">
                {workout.completed_at
                  ? `Completed on ${new Date(workout.completed_at).toLocaleString()}`
                  : workout.started_at
                  ? `Started on ${new Date(workout.started_at).toLocaleString()}`
                  : 'Draft workout'}
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
                <div className="text-sm text-green-600 font-medium">Exercises</div>
                <div className="text-2xl font-bold text-green-900 mt-1">
                  {workout.exercises.length}
                </div>
              </div>
            </div>

            {/* Tags */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold">Tags</h3>
                {workout.state === 'completed' && (
                  <button
                    onClick={() => setEditingTags(!editingTags)}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    {editingTags ? 'Cancel' : 'Edit Tags'}
                  </button>
                )}
              </div>
              {editingTags ? (
                <div>
                  <TagInput
                    selectedTags={workoutTags}
                    onTagsChange={handleTagsChange}
                    placeholder="Add tags..."
                  />
                  {savingTags && (
                    <p className="text-sm text-gray-500 mt-2">Saving tags...</p>
                  )}
                </div>
              ) : (
                <TagDisplay tags={workoutTags} size="md" />
              )}
            </div>

            {/* Volume Breakdown */}
            {!loading && (
              <VolumeBreakdown workout={workout} exerciseDetails={exerciseDetails} />
            )}

            {/* Exercise Details */}
            <div>
              <h3 className="text-lg font-semibold mb-3">Exercise Details</h3>
              <div className="space-y-3">
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
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h4 className="font-semibold">
                            {exerciseDetail?.name || `Exercise ${exercise.exercise_id}`}
                          </h4>
                          <div className="text-sm text-gray-600 mt-1">
                            {exercise.sets.length} set{exercise.sets.length !== 1 ? 's' : ''} •{' '}
                            {exerciseVolume.toLocaleString()} lbs total volume
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
                      <div className="mt-3 space-y-1">
                        {exercise.sets.map((set) => (
                          <div key={set.id} className="text-sm text-gray-600">
                            Set {set.set_number}: {set.reps || '—'} reps × {set.weight || '—'} lbs
                            {set.rest_seconds && (
                              <span className="text-gray-400 ml-2">
                                (rest: {Math.floor(set.rest_seconds / 60)}:
                                {String(set.rest_seconds % 60).padStart(2, '0')})
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-6 border-t bg-gray-50">
            <div className="flex justify-end">
              <button
                onClick={onClose}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
