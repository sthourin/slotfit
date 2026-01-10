/**
 * PR Notification Component
 * Shows new personal records achieved in the workout
 */
import { type WorkoutSession, type WorkoutExercise } from '../../services/workouts'
import { type Exercise } from '../../services/exercises'
import { personalRecordApi, type PersonalRecord } from '../../services/personalRecords'
import { useState, useEffect } from 'react'

interface PRNotificationProps {
  workout: WorkoutSession
  exerciseDetails: Map<number, Exercise>
}

export default function PRNotification({ workout, exerciseDetails }: PRNotificationProps) {
  const [newPRs, setNewPRs] = useState<PersonalRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadPRs = async () => {
      try {
        // Get all PRs achieved in this workout
        const response = await personalRecordApi.list()
        const workoutPRs = response.records.filter(
          (pr) => pr.workout_session_id === workout.id
        )
        setNewPRs(workoutPRs)
      } catch (error) {
        console.error('Failed to load personal records:', error)
      } finally {
        setLoading(false)
      }
    }

    loadPRs()
  }, [workout.id])

  if (loading) {
    return (
      <div className="text-center py-4">
        <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (newPRs.length === 0) {
    return null
  }

  const getPRTypeLabel = (type: string) => {
    switch (type) {
      case 'weight':
        return 'Max Weight'
      case 'reps':
        return 'Max Reps'
      case 'volume':
        return 'Max Volume'
      case 'time':
        return 'Best Time'
      default:
        return type
    }
  }

  return (
    <div className="bg-yellow-50 border-2 border-yellow-400 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <div className="text-2xl">🏆</div>
        <div className="flex-1">
          <h3 className="font-semibold text-yellow-900 mb-2">
            New Personal Records!
          </h3>
          <div className="space-y-2">
            {newPRs.map((pr) => {
              const exercise = exerciseDetails.get(pr.exercise_id)
              return (
                <div
                  key={pr.id}
                  className="bg-white rounded p-3 border border-yellow-300"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900">
                        {exercise?.name || `Exercise ${pr.exercise_id}`}
                      </div>
                      <div className="text-sm text-gray-600">
                        {getPRTypeLabel(pr.record_type)}: {pr.value}
                        {pr.record_type === 'weight' && ' lbs'}
                        {pr.record_type === 'reps' && ' reps'}
                        {pr.record_type === 'volume' && ' lbs'}
                        {pr.record_type === 'time' && ' sec'}
                      </div>
                    </div>
                    <span className="px-2 py-1 bg-yellow-200 text-yellow-900 rounded text-xs font-medium">
                      NEW PR!
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
