/**
 * Quick Fill Modal Component
 * Uses AI recommendations to quickly fill all slots with exercises
 */
import { useState, useEffect } from 'react'
import { type RoutineTemplate, type RoutineSlot } from '../../services/routines'
import { recommendationApi, type ExerciseRecommendation } from '../../services/recommendations'
import { exerciseApi, type Exercise } from '../../services/exercises'

interface QuickFillModalProps {
  routine: RoutineTemplate
  equipmentProfileId: number | null
  onFill: (filledExercises: Map<number, { exerciseId: number; exerciseName: string }>) => void
  onClose: () => void
}

export default function QuickFillModal({
  routine,
  equipmentProfileId,
  onFill,
  onClose,
}: QuickFillModalProps) {
  const [recommendations, setRecommendations] = useState<
    Map<number, ExerciseRecommendation[]>
  >(new Map())
  const [loading, setLoading] = useState(false)
  const [selectedExercises, setSelectedExercises] = useState<
    Map<number, { exerciseId: number; exerciseName: string }>
  >(new Map())
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRecommendations()
  }, [])

  const loadRecommendations = async () => {
    setLoading(true)
    setError(null)

    try {
      const equipmentIds = equipmentProfileId
        ? await getEquipmentIds(equipmentProfileId)
        : []

      // Get recommendations for each slot
      const recMap = new Map<number, ExerciseRecommendation[]>()
      
      for (const slot of routine.slots) {
        try {
          const response = await recommendationApi.getRecommendations({
            muscle_group_ids: slot.muscle_group_ids,
            available_equipment_ids: equipmentIds,
            limit: 5,
          })
          
          recMap.set(slot.id, response.recommendations)
          
          // Auto-select top recommendation for each slot
          if (response.recommendations.length > 0) {
            const topRec = response.recommendations[0]
            setSelectedExercises((prev) => {
              const next = new Map(prev)
              next.set(slot.id, {
                exerciseId: topRec.exercise_id,
                exerciseName: topRec.exercise_name,
              })
              return next
            })
          }
        } catch (err) {
          console.error(`Failed to get recommendations for slot ${slot.id}:`, err)
        }
      }

      setRecommendations(recMap)
    } catch (err) {
      console.error('Failed to load recommendations:', err)
      setError('Failed to load recommendations. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const getEquipmentIds = async (profileId: number): Promise<number[]> => {
    try {
      const { equipmentProfileApi } = await import('../../services/equipmentProfiles')
      const profile = await equipmentProfileApi.get(profileId)
      return profile.equipment_ids
    } catch (err) {
      console.error('Failed to load equipment profile:', err)
      return []
    }
  }

  const handleSelectExercise = (
    slotId: number,
    exerciseId: number,
    exerciseName: string
  ) => {
    setSelectedExercises((prev) => {
      const next = new Map(prev)
      next.set(slotId, { exerciseId, exerciseName })
      return next
    })
  }

  const handleApply = () => {
    onFill(selectedExercises)
  }

  const allSlotsFilled = routine.slots.every((slot) =>
    selectedExercises.has(slot.id)
  )

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="text-2xl font-bold">Quick-Fill with AI Recommendations</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-4 text-gray-600">Loading AI recommendations...</p>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-600 mb-4">{error}</p>
              <button
                onClick={loadRecommendations}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {routine.slots.map((slot, index) => {
                const slotRecs = recommendations.get(slot.id) || []
                const selected = selectedExercises.get(slot.id)

                return (
                  <div key={slot.id} className="border rounded-lg p-4">
                    <div className="font-semibold mb-3">
                      Slot {index + 1}: {slot.name || `Slot ${index + 1}`}
                    </div>
                    {slotRecs.length === 0 ? (
                      <p className="text-sm text-gray-500">
                        No recommendations available for this slot.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {slotRecs.map((rec) => {
                          const isSelected =
                            selected?.exerciseId === rec.exercise_id

                          return (
                            <button
                              key={rec.exercise_id}
                              onClick={() =>
                                handleSelectExercise(
                                  slot.id,
                                  rec.exercise_id,
                                  rec.exercise_name
                                )
                              }
                              className={`w-full text-left p-3 border-2 rounded-lg transition-colors ${
                                isSelected
                                  ? 'border-blue-600 bg-blue-50'
                                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex-1">
                                  <div className="font-medium">
                                    {rec.exercise_name}
                                  </div>
                                  {rec.reasoning && (
                                    <div className="text-xs text-gray-600 mt-1">
                                      {rec.reasoning}
                                    </div>
                                  )}
                                  <div className="text-xs text-gray-500 mt-1">
                                    Priority: {(rec.priority_score * 100).toFixed(0)}%
                                  </div>
                                </div>
                                {isSelected && (
                                  <div className="ml-4 text-blue-600">
                                    <svg
                                      className="w-5 h-5"
                                      fill="none"
                                      stroke="currentColor"
                                      viewBox="0 0 24 24"
                                    >
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M5 13l4 4L19 7"
                                      />
                                    </svg>
                                  </div>
                                )}
                              </div>
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex items-center justify-between">
          <div className="text-sm text-gray-600">
            {selectedExercises.size} of {routine.slots.length} slots filled
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleApply}
              disabled={!allSlotsFilled}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              Apply Selections
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
