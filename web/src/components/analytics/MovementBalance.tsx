/**
 * Movement Balance Component
 * Shows push/pull and compound/isolation balance
 */
import { useState, useEffect } from 'react'
import { workoutApi } from '../../services/workouts'
import { exerciseApi, type Exercise } from '../../services/exercises'

export default function MovementBalance() {
  const [balance, setBalance] = useState<{
    push: number
    pull: number
    compound: number
    isolation: number
  } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadBalance()
  }, [])

  const loadBalance = async () => {
    setLoading(true)
    try {
      // Get recent workouts
      const response = await workoutApi.list({ limit: 10 })
      const workouts = response.workouts.filter((w) => w.state === 'completed')

      // Load exercise details
      const exerciseIds = new Set<number>()
      workouts.forEach((workout) => {
        workout.exercises.forEach((ex) => {
          if (ex.exercise_id) {
            exerciseIds.add(ex.exercise_id)
          }
        })
      })

      const exercises = await Promise.all(
        Array.from(exerciseIds).map((id) => exerciseApi.get(id).catch(() => null))
      )

      const exerciseMap = new Map<number, Exercise>()
      exercises.forEach((ex, idx) => {
        if (ex) {
          exerciseMap.set(Array.from(exerciseIds)[idx], ex)
        }
      })

      // Calculate balance
      let push = 0
      let pull = 0
      let compound = 0
      let isolation = 0

      workouts.forEach((workout) => {
        workout.exercises.forEach((ex) => {
          const exercise = exerciseMap.get(ex.exercise_id)
          if (exercise) {
            if (exercise.force_type === 'Push') push++
            if (exercise.force_type === 'Pull') pull++
            if (exercise.mechanics === 'Compound') compound++
            if (exercise.mechanics === 'Isolation') isolation++
          }
        })
      })

      setBalance({ push, pull, compound, isolation })
    } catch (error) {
      console.error('Failed to load movement balance:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!balance) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No movement balance data available</p>
      </div>
    )
  }

  const totalForce = balance.push + balance.pull
  const totalMechanics = balance.compound + balance.isolation

  const pushPercentage = totalForce > 0 ? (balance.push / totalForce) * 100 : 0
  const pullPercentage = totalForce > 0 ? (balance.pull / totalForce) * 100 : 0
  const compoundPercentage = totalMechanics > 0 ? (balance.compound / totalMechanics) * 100 : 0
  const isolationPercentage = totalMechanics > 0 ? (balance.isolation / totalMechanics) * 100 : 0

  return (
    <div className="space-y-6">
      {/* Push/Pull Balance */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Push vs Pull</h3>
        <div className="space-y-2">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">Push</span>
              <span className="text-sm text-gray-600">
                {balance.push} ({pushPercentage.toFixed(0)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-blue-600 h-4 rounded-full transition-all"
                style={{ width: `${pushPercentage}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">Pull</span>
              <span className="text-sm text-gray-600">
                {balance.pull} ({pullPercentage.toFixed(0)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-purple-600 h-4 rounded-full transition-all"
                style={{ width: `${pullPercentage}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Compound/Isolation Balance */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Compound vs Isolation</h3>
        <div className="space-y-2">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">Compound</span>
              <span className="text-sm text-gray-600">
                {balance.compound} ({compoundPercentage.toFixed(0)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-green-600 h-4 rounded-full transition-all"
                style={{ width: `${compoundPercentage}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">Isolation</span>
              <span className="text-sm text-gray-600">
                {balance.isolation} ({isolationPercentage.toFixed(0)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-orange-600 h-4 rounded-full transition-all"
                style={{ width: `${isolationPercentage}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
