/**
 * Volume Breakdown Component
 * Shows volume per muscle group for the workout
 */
import { type WorkoutSession, type WorkoutExercise } from '../../services/workouts'
import { type Exercise } from '../../services/exercises'
import { useState, useMemo } from 'react'

interface VolumeBreakdownProps {
  workout: WorkoutSession
  exerciseDetails: Map<number, Exercise>
}

interface MuscleGroupVolume {
  muscleGroupId: number
  muscleGroupName: string
  sets: number
  reps: number
  volume: number
}

export default function VolumeBreakdown({
  workout,
  exerciseDetails,
}: VolumeBreakdownProps) {
  const volumeByMuscleGroup = useMemo(() => {
    const volumeMap = new Map<number, MuscleGroupVolume>()

    workout.exercises.forEach((exercise) => {
      const exerciseDetail = exerciseDetails.get(exercise.exercise_id)
      if (!exerciseDetail) return

      // Calculate volume for this exercise
      const exerciseVolume = exercise.sets.reduce(
        (sum, set) => sum + (set.reps || 0) * (set.weight || 0),
        0
      )
      const exerciseReps = exercise.sets.reduce(
        (sum, set) => sum + (set.reps || 0),
        0
      )

      // Add to each muscle group this exercise targets
      exerciseDetail.muscle_groups.forEach((mg) => {
        const existing = volumeMap.get(mg.id)
        if (existing) {
          existing.sets += exercise.sets.length
          existing.reps += exerciseReps
          existing.volume += exerciseVolume
        } else {
          volumeMap.set(mg.id, {
            muscleGroupId: mg.id,
            muscleGroupName: mg.name,
            sets: exercise.sets.length,
            reps: exerciseReps,
            volume: exerciseVolume,
          })
        }
      })
    })

    return Array.from(volumeMap.values()).sort((a, b) => b.volume - a.volume)
  }, [workout.exercises, exerciseDetails])

  if (volumeByMuscleGroup.length === 0) {
    return null
  }

  const maxVolume = Math.max(...volumeByMuscleGroup.map((v) => v.volume))

  return (
    <div>
      <h3 className="text-lg font-semibold mb-3">Volume by Muscle Group</h3>
      <div className="space-y-3">
        {volumeByMuscleGroup.map((mgVolume) => {
          const percentage = maxVolume > 0 ? (mgVolume.volume / maxVolume) * 100 : 0

          return (
            <div key={mgVolume.muscleGroupId}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex-1">
                  <div className="font-medium text-gray-900">{mgVolume.muscleGroupName}</div>
                  <div className="text-sm text-gray-600">
                    {mgVolume.sets} sets • {mgVolume.reps} reps • {mgVolume.volume.toLocaleString()} lbs
                  </div>
                </div>
                <div className="text-sm font-semibold text-gray-700 ml-4">
                  {mgVolume.volume.toLocaleString()} lbs
                </div>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
