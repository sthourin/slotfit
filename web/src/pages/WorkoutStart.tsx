/**
 * Workout Start Page
 * Flow for starting a new workout from a routine
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import RoutineSelector from '../components/workout/RoutineSelector'
import EquipmentProfileSelector from '../components/workout/EquipmentProfileSelector'
import QuickFillModal from '../components/workout/QuickFillModal'
import LastWorkoutOption from '../components/workout/LastWorkoutOption'
import { useRoutineStore } from '../stores/routineStore'
import { useEquipmentStore } from '../stores/equipmentStore'
import { useWorkoutStore } from '../stores/workoutStore'
import { routineApi, type RoutineTemplate } from '../services/routines'
import { workoutApi, type WorkoutSession } from '../services/workouts'
import { exerciseApi, type Exercise } from '../services/exercises'

interface SlotExercise {
  slotId: number
  slotName: string | null
  exerciseId: number | null
  exerciseName: string | null
}

export default function WorkoutStart() {
  const navigate = useNavigate()
  const { loadProfiles, getSelectedProfile } = useEquipmentStore()
  const { initializeWorkoutWithSlots } = useWorkoutStore()
  
  // Step 1: Routine selection
  const [selectedRoutineId, setSelectedRoutineId] = useState<number | null>(null)
  const [selectedRoutine, setSelectedRoutine] = useState<RoutineTemplate | null>(null)
  const [loadingRoutine, setLoadingRoutine] = useState(false)
  
  // Step 2: Equipment profile
  const [selectedEquipmentProfileId, setSelectedEquipmentProfileId] = useState<number | null>(null)
  
  // Step 3: Exercise pre-fill options
  const [showQuickFillModal, setShowQuickFillModal] = useState(false)
  const [showLastWorkoutOption, setShowLastWorkoutOption] = useState(false)
  const [lastWorkout, setLastWorkout] = useState<WorkoutSession | null>(null)
  const [loadingLastWorkout, setLoadingLastWorkout] = useState(false)
  
  // Step 4: Slot exercises (review before starting)
  const [slotExercises, setSlotExercises] = useState<SlotExercise[]>([])
  const [initializing, setInitializing] = useState(false)

  // Load equipment profiles on mount
  useEffect(() => {
    loadProfiles().catch(console.error)
  }, [loadProfiles])

  // Set default equipment profile when profiles load
  useEffect(() => {
    const defaultProfile = getSelectedProfile()
    if (defaultProfile && !selectedEquipmentProfileId) {
      setSelectedEquipmentProfileId(defaultProfile.id)
    }
  }, [getSelectedProfile, selectedEquipmentProfileId])

  // Load routine when selected
  useEffect(() => {
    if (selectedRoutineId) {
      setLoadingRoutine(true)
      routineApi
        .get(selectedRoutineId)
        .then((routine) => {
          setSelectedRoutine(routine)
          // Initialize slot exercises array
          setSlotExercises(
            routine.slots.map((slot) => ({
              slotId: slot.id,
              slotName: slot.name,
              exerciseId: slot.selected_exercise_id || null,
              exerciseName: null,
            }))
          )
          setLoadingRoutine(false)
        })
        .catch((error) => {
          console.error('Failed to load routine:', error)
          setLoadingRoutine(false)
        })
    }
  }, [selectedRoutineId])

  // Load last completed workout for this routine
  useEffect(() => {
    if (selectedRoutineId) {
      setLoadingLastWorkout(true)
      workoutApi
        .list({ limit: 10 })
        .then((response) => {
          // Find the most recent completed workout for this routine
          const lastCompleted = response.workouts.find(
            (w) =>
              w.routine_template_id === selectedRoutineId &&
              w.state === 'completed'
          )
          setLastWorkout(lastCompleted || null)
          setLoadingLastWorkout(false)
        })
        .catch((error) => {
          console.error('Failed to load last workout:', error)
          setLoadingLastWorkout(false)
        })
    }
  }, [selectedRoutineId])

  // Load exercise names for slot exercises
  useEffect(() => {
    const exerciseIds = slotExercises
      .map((se) => se.exerciseId)
      .filter((id): id is number => id !== null)
    
    if (exerciseIds.length > 0) {
      Promise.all(
        exerciseIds.map((id) =>
          exerciseApi
            .get(id)
            .then((exercise) => ({ id, name: exercise.name }))
            .catch(() => ({ id, name: 'Unknown Exercise' }))
        )
      ).then((exercises) => {
        const exerciseMap = new Map(exercises.map((e) => [e.id, e.name]))
        setSlotExercises((prev) =>
          prev.map((se) => ({
            ...se,
            exerciseName: se.exerciseId ? exerciseMap.get(se.exerciseId) || null : null,
          }))
        )
      })
    }
  }, [slotExercises.map((se) => se.exerciseId).join(',')])

  const handleQuickFill = async (filledExercises: Map<number, { exerciseId: number; exerciseName: string }>) => {
    // Update slot exercises with quick-filled selections
    setSlotExercises((prev) =>
      prev.map((se) => {
        const filled = filledExercises.get(se.slotId)
        return filled
          ? {
              ...se,
              exerciseId: filled.exerciseId,
              exerciseName: filled.exerciseName,
            }
          : se
      })
    )
    setShowQuickFillModal(false)
  }

  const handleCopyLastWorkout = () => {
    if (!lastWorkout) return

    // Map last workout exercises to slot exercises
    const exerciseMap = new Map<number, { exerciseId: number; exerciseName: string }>()
    
    lastWorkout.exercises.forEach((we) => {
      if (we.slot_id && we.exercise_id) {
        // Find exercise name
        exerciseApi
          .get(we.exercise_id)
          .then((exercise) => {
            exerciseMap.set(we.slot_id!, {
              exerciseId: we.exercise_id,
              exerciseName: exercise.name,
            })
            
            // Update all slots once we have all names
            if (exerciseMap.size === lastWorkout.exercises.length) {
              setSlotExercises((prev) =>
                prev.map((se) => {
                  const filled = exerciseMap.get(se.slotId)
                  return filled
                    ? {
                        ...se,
                        exerciseId: filled.exerciseId,
                        exerciseName: filled.exerciseName,
                      }
                    : se
                })
              )
            }
          })
          .catch(console.error)
      }
    })
    
    setShowLastWorkoutOption(false)
  }

  const handleStartWorkout = async () => {
    if (!selectedRoutineId || !selectedRoutine) return

    setInitializing(true)
    try {
      // Initialize workout with pre-filled exercises
      await initializeWorkoutWithSlots(
        selectedRoutineId,
        slotExercises.map((se) => ({
          slotId: se.slotId,
          exerciseId: se.exerciseId,
          exerciseName: se.exerciseName,
        })),
        selectedEquipmentProfileId || undefined
      )

      // Navigate to workout page
      navigate(`/workout`)
    } catch (error) {
      console.error('Failed to start workout:', error)
      alert('Failed to start workout. Please try again.')
    } finally {
      setInitializing(false)
    }
  }

  const canStart = selectedRoutineId && selectedRoutine && slotExercises.length > 0

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-4xl">
        <h1 className="text-3xl font-bold mb-8">Start Workout</h1>

        {/* Step 1: Select Routine */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">1. Select Routine</h2>
          <RoutineSelector
            selectedRoutineId={selectedRoutineId}
            onSelectRoutine={setSelectedRoutineId}
            loading={loadingRoutine}
          />
        </div>

        {/* Step 2: Select Equipment Profile */}
        {selectedRoutineId && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">2. Select Equipment Profile</h2>
            <EquipmentProfileSelector
              selectedProfileId={selectedEquipmentProfileId}
              onSelectProfile={setSelectedEquipmentProfileId}
            />
          </div>
        )}

        {/* Step 3: Pre-fill Options */}
        {selectedRoutineId && selectedRoutine && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">3. Pre-fill Exercises (Optional)</h2>
            <div className="space-y-4">
              <button
                onClick={() => setShowQuickFillModal(true)}
                className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Quick-Fill with AI Recommendations
              </button>

              {lastWorkout && (
                <LastWorkoutOption
                  lastWorkout={lastWorkout}
                  onCopy={handleCopyLastWorkout}
                  loading={loadingLastWorkout}
                />
              )}
            </div>
          </div>
        )}

        {/* Step 4: Review Slot Exercises */}
        {selectedRoutine && slotExercises.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">4. Review Exercises</h2>
            <div className="space-y-3">
              {slotExercises.map((se, index) => (
                <div
                  key={se.slotId}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex-1">
                    <div className="font-medium">
                      Slot {index + 1}: {se.slotName || `Slot ${index + 1}`}
                    </div>
                    <div className="text-sm text-gray-600">
                      {se.exerciseName || (
                        <span className="text-gray-400 italic">No exercise selected</span>
                      )}
                    </div>
                  </div>
                  {!se.exerciseId && (
                    <span className="text-xs text-yellow-600 bg-yellow-50 px-2 py-1 rounded">
                      Will select during workout
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Start Workout Button */}
        {canStart && (
          <div className="flex justify-end">
            <button
              onClick={handleStartWorkout}
              disabled={initializing}
              className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-semibold"
            >
              {initializing ? 'Starting...' : 'Start Workout'}
            </button>
          </div>
        )}

        {/* Quick Fill Modal */}
        {showQuickFillModal && selectedRoutine && (
          <QuickFillModal
            routine={selectedRoutine}
            equipmentProfileId={selectedEquipmentProfileId}
            onFill={handleQuickFill}
            onClose={() => setShowQuickFillModal(false)}
          />
        )}
      </div>
    </div>
  )
}
