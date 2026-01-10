/**
 * Recommendations Panel Component
 * Displays AI exercise recommendations
 */
import { type ExerciseRecommendation } from '../../services/recommendations'
import { exerciseApi, type Exercise } from '../../services/exercises'
import { useState } from 'react'

interface RecommendationsPanelProps {
  recommendations: ExerciseRecommendation[]
  loading: boolean
  onSelectExercise: (exerciseId: number, exerciseName: string) => void
}

export default function RecommendationsPanel({
  recommendations,
  loading,
  onSelectExercise,
}: RecommendationsPanelProps) {
  const [loadingDetails, setLoadingDetails] = useState<Set<number>>(new Set())
  const [exerciseDetails, setExerciseDetails] = useState<Map<number, Exercise>>(new Map())

  const loadExerciseDetails = async (exerciseId: number) => {
    if (exerciseDetails.has(exerciseId)) return

    setLoadingDetails((prev) => new Set(prev).add(exerciseId))
    try {
      const exercise = await exerciseApi.get(exerciseId)
      setExerciseDetails((prev) => new Map(prev).set(exerciseId, exercise))
    } catch (error) {
      console.error('Failed to load exercise details:', error)
    } finally {
      setLoadingDetails((prev) => {
        const next = new Set(prev)
        next.delete(exerciseId)
        return next
      })
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-4 text-gray-600">Loading AI recommendations...</p>
      </div>
    )
  }

  if (recommendations.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No recommendations available. Try searching for exercises instead.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Top Recommendations</h3>
      <div className="space-y-3">
        {recommendations.map((rec, index) => {
          const exercise = exerciseDetails.get(rec.exercise_id)
          const isLoading = loadingDetails.has(rec.exercise_id)

          return (
            <div
              key={rec.exercise_id}
              className="border rounded-lg p-4 hover:bg-gray-50 transition-colors cursor-pointer"
              onClick={() => {
                loadExerciseDetails(rec.exercise_id)
                onSelectExercise(rec.exercise_id, rec.exercise_name)
              }}
              onMouseEnter={() => loadExerciseDetails(rec.exercise_id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-600 rounded-full font-semibold text-sm">
                      {index + 1}
                    </span>
                    <h4 className="text-lg font-semibold">{rec.exercise_name}</h4>
                    <span className="text-sm text-gray-500">
                      {(rec.priority_score * 100).toFixed(0)}% match
                    </span>
                  </div>

                  <p className="text-sm text-gray-600 mb-3">{rec.reasoning}</p>

                  {/* Factors */}
                  <div className="flex flex-wrap gap-2 mb-3">
                    {rec.factors.frequency && (
                      <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                        {rec.factors.frequency}
                      </span>
                    )}
                    {rec.factors.last_performed && (
                      <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                        {rec.factors.last_performed}
                      </span>
                    )}
                    {rec.factors.progression_opportunity && (
                      <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                        Progression
                      </span>
                    )}
                    {rec.factors.variety_boost && (
                      <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">
                        Variety
                      </span>
                    )}
                    {rec.factors.movement_balance && (
                      <span className="px-2 py-1 text-xs bg-indigo-100 text-indigo-800 rounded">
                        {rec.factors.movement_balance}
                      </span>
                    )}
                    {rec.factors.weekly_volume_status && (
                      <span className="px-2 py-1 text-xs bg-orange-100 text-orange-800 rounded">
                        {rec.factors.weekly_volume_status}
                      </span>
                    )}
                  </div>

                  {/* Exercise details (if loaded) */}
                  {isLoading && (
                    <div className="text-sm text-gray-500">Loading details...</div>
                  )}
                  {exercise && (
                    <div className="mt-3 space-y-2">
                      {exercise.description && (
                        <p className="text-sm text-gray-600">{exercise.description}</p>
                      )}
                      {exercise.difficulty && (
                        <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                          {exercise.difficulty}
                        </span>
                      )}
                      {(exercise.short_demo_url || exercise.in_depth_url) && (
                        <div className="flex gap-2 mt-2">
                          {exercise.short_demo_url && (
                            <a
                              href={exercise.short_demo_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="text-sm text-blue-600 hover:text-blue-800 underline"
                            >
                              Watch Demo
                            </a>
                          )}
                          {exercise.in_depth_url && (
                            <a
                              href={exercise.in_depth_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="text-sm text-blue-600 hover:text-blue-800 underline"
                            >
                              Learn More
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    loadExerciseDetails(rec.exercise_id)
                    onSelectExercise(rec.exercise_id, rec.exercise_name)
                  }}
                  className="ml-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Select
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
