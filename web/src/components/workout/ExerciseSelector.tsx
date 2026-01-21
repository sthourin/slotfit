/**
 * Exercise Selector Modal Component
 * Allows selecting an exercise for a slot with AI recommendations, search, and "Why Not" section
 */
import { useState, useEffect, useMemo } from 'react'
import { useUIStore } from '../../stores/uiStore'
import { useWorkoutStore } from '../../stores/workoutStore'
import { useEquipmentStore } from '../../stores/equipmentStore'
import { recommendationApi, type ExerciseRecommendation, type NotRecommendedExercise } from '../../services/recommendations'
import { exerciseApi, type Exercise } from '../../services/exercises'
import RecommendationsPanel from './RecommendationsPanel'
import WhyNotSection from './WhyNotSection'
import ExerciseSearch from './ExerciseSearch'

interface ExerciseSelectorProps {
  slotIndex: number
  muscleGroupIds: number[]
  slotId: number | null
}

export default function ExerciseSelector({ slotIndex, muscleGroupIds, slotId }: ExerciseSelectorProps) {
  const { modals, closeModal } = useUIStore()
  const { activeWorkout, selectExerciseForSlot } = useWorkoutStore()
  const { getSelectedProfile } = useEquipmentStore()
  
  const [recommendations, setRecommendations] = useState<ExerciseRecommendation[]>([])
  const [notRecommended, setNotRecommended] = useState<NotRecommendedExercise[]>([])
  const [loadingRecommendations, setLoadingRecommendations] = useState(false)
  const [searchResults, setSearchResults] = useState<Exercise[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<'recommendations' | 'search'>('recommendations')
  const [loadingExercise, setLoadingExercise] = useState(false)

  // Check if this modal instance should be open (match slotIndex from modal data)
  const modalData = modals.exerciseSelector.data
  const isOpen = modals.exerciseSelector.isOpen && modalData?.slotIndex === slotIndex
  const equipmentProfile = getSelectedProfile()
  const availableEquipmentIds = equipmentProfile?.equipment_ids || []

  // Load recommendations when modal opens
  useEffect(() => {
    if (isOpen && muscleGroupIds.length > 0) {
      loadRecommendations()
    }
  }, [isOpen, muscleGroupIds.join(','), availableEquipmentIds.join(',')])

  const loadRecommendations = async () => {
    setLoadingRecommendations(true)
    try {
      const response = await recommendationApi.getRecommendations({
        muscle_group_ids: muscleGroupIds,
        available_equipment_ids: availableEquipmentIds,
        workout_session_id: activeWorkout?.id || null,
        limit: 5,
      })
      setRecommendations(response.recommendations)
      setNotRecommended(response.not_recommended || [])
    } catch (error) {
      console.error('Failed to load recommendations:', error)
    } finally {
      setLoadingRecommendations(false)
    }
  }

  const handleSelectExercise = async (exerciseId: number, exerciseName: string) => {
    setLoadingExercise(true)
    try {
      // Update workout store (now async)
      await selectExerciseForSlot(slotIndex, exerciseId, exerciseName)
      
      // Close modal
      closeModal('exerciseSelector')
    } catch (error) {
      console.error('Failed to select exercise:', error)
      alert('Failed to select exercise. Please try again.')
    } finally {
      setLoadingExercise(false)
    }
  }

  const handleSearch = async (query: string) => {
    setSearchQuery(query)
    if (!query.trim()) {
      setSearchResults([])
      return
    }

    try {
      const response = await exerciseApi.list({
        search: query,
        muscle_group_ids: muscleGroupIds,
        limit: 20,
      })
      setSearchResults(response.exercises)
    } catch (error) {
      console.error('Failed to search exercises:', error)
      setSearchResults([])
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={() => closeModal('exerciseSelector')}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b">
            <h2 className="text-2xl font-bold">Select Exercise</h2>
            <button
              onClick={() => closeModal('exerciseSelector')}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b">
            <button
              onClick={() => setActiveTab('recommendations')}
              className={`px-6 py-3 font-medium transition-colors ${
                activeTab === 'recommendations'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              AI Recommendations
            </button>
            <button
              onClick={() => setActiveTab('search')}
              className={`px-6 py-3 font-medium transition-colors ${
                activeTab === 'search'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Search All Exercises
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === 'recommendations' ? (
              <div className="space-y-6">
                <RecommendationsPanel
                  recommendations={recommendations}
                  loading={loadingRecommendations}
                  onSelectExercise={handleSelectExercise}
                />

                {notRecommended.length > 0 && (
                  <WhyNotSection notRecommended={notRecommended} />
                )}
              </div>
            ) : (
              <ExerciseSearch
                searchQuery={searchQuery}
                searchResults={searchResults}
                onSearch={handleSearch}
                onSelectExercise={handleSelectExercise}
              />
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t bg-gray-50">
            <div className="flex justify-end gap-3">
              <button
                onClick={() => closeModal('exerciseSelector')}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
