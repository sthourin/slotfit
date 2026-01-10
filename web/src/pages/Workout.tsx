/**
 * Active Workout Page
 * Main interface for executing a workout
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkoutStore } from '../stores/workoutStore'
import SlotProgressBar from '../components/workout/SlotProgressBar'
import CurrentSlot from '../components/workout/CurrentSlot'
import ExercisePanel from '../components/workout/ExercisePanel'
import SetTracker from '../components/workout/SetTracker'
import RestTimer from '../components/workout/RestTimer'
import WorkoutControls from '../components/workout/WorkoutControls'
import { exerciseApi, type Exercise } from '../services/exercises'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { useWorkoutNavigation } from '../hooks/useWorkoutNavigation'

export default function Workout() {
  const navigate = useNavigate()
  const {
    activeWorkout,
    activeSlots,
    currentSlotIndex,
    loading,
    startWorkout,
    pauseWorkout,
    resumeWorkout,
    completeWorkout,
    abandonWorkout,
    setCurrentSlot,
  } = useWorkoutStore()

  const [currentExercise, setCurrentExercise] = useState<Exercise | null>(null)
  const [loadingExercise, setLoadingExercise] = useState(false)
  const [restTimerRunning, setRestTimerRunning] = useState(false)
  const [showShortcuts, setShowShortcuts] = useState(false)

  // Load exercise details for current slot
  useEffect(() => {
    if (currentSlotIndex !== null && activeSlots[currentSlotIndex]) {
      const slot = activeSlots[currentSlotIndex]
      if (slot.exerciseId) {
        setLoadingExercise(true)
        exerciseApi
          .get(slot.exerciseId)
          .then(setCurrentExercise)
          .catch((error) => {
            console.error('Failed to load exercise:', error)
            setCurrentExercise(null)
          })
          .finally(() => setLoadingExercise(false))
      } else {
        setCurrentExercise(null)
      }
    }
  }, [currentSlotIndex, activeSlots])

  // Auto-start workout if in draft state
  useEffect(() => {
    if (activeWorkout && activeWorkout.state === 'draft') {
      startWorkout().catch(console.error)
    }
  }, [activeWorkout, startWorkout])

  // Redirect if no active workout
  useEffect(() => {
    if (!loading && !activeWorkout) {
      navigate('/workout/start')
    }
  }, [activeWorkout, loading, navigate])

  // Workout navigation
  const navigation = useWorkoutNavigation({
    activeSlots,
    currentSlotIndex,
    onRestTimerToggle: (isRunning) => setRestTimerRunning(isRunning),
  })

  // Keyboard shortcuts
  useKeyboardShortcuts({
    enabled: activeWorkout?.state === 'active' || activeWorkout?.state === 'paused',
    handlers: {
      onPreviousSlot: navigation.goToPreviousSlot,
      onNextSlot: navigation.goToNextSlot,
      onSkipSlot: navigation.skipCurrentSlot,
      onCompleteSet: () => {
        // If slot is in progress, add a set; otherwise complete the slot
        if (currentSlot?.slotState === 'in_progress') {
          navigation.addSetToCurrentSlot()
        } else if (currentSlot?.slotState === 'not_started') {
          navigation.startCurrentSlot()
        } else {
          navigation.completeCurrentSlot()
        }
      },
      onToggleRestTimer: navigation.toggleRestTimer,
      onCancel: () => {
        // Close any modals or cancel editing
        setShowShortcuts(false)
      },
    },
  })

  if (loading || !activeWorkout) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading workout...</p>
        </div>
      </div>
    )
  }

  const currentSlot =
    currentSlotIndex !== null ? activeSlots[currentSlotIndex] : null

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-6 max-w-6xl">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-bold">Active Workout</h1>
            <div className="flex items-center gap-2">
              {activeWorkout.state === 'active' && (
                <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                  Active
                </span>
              )}
              {activeWorkout.state === 'paused' && (
                <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                  Paused
                </span>
              )}
              <button
                onClick={() => setShowShortcuts(!showShortcuts)}
                className="px-3 py-1 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                title="Keyboard shortcuts"
              >
                ⌨️
              </button>
            </div>
          </div>
          
          {/* Keyboard Shortcuts Help */}
          {showShortcuts && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-blue-900 mb-2">Keyboard Shortcuts</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm text-blue-800">
                    <div><kbd className="px-2 py-1 bg-white rounded border">←</kbd> Previous slot</div>
                    <div><kbd className="px-2 py-1 bg-white rounded border">→</kbd> Next slot</div>
                    <div><kbd className="px-2 py-1 bg-white rounded border">S</kbd> Skip slot</div>
                    <div><kbd className="px-2 py-1 bg-white rounded border">Enter</kbd> Add set / Complete</div>
                    <div><kbd className="px-2 py-1 bg-white rounded border">Space</kbd> Toggle rest timer</div>
                    <div><kbd className="px-2 py-1 bg-white rounded border">Esc</kbd> Cancel / Close</div>
                  </div>
                </div>
                <button
                  onClick={() => setShowShortcuts(false)}
                  className="text-blue-600 hover:text-blue-800"
                >
                  ✕
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Slot Progress Bar */}
        <div className="mb-6">
          <SlotProgressBar
            slots={activeSlots}
            currentSlotIndex={currentSlotIndex}
            onSelectSlot={setCurrentSlot}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Current Slot & Exercise */}
          <div className="lg:col-span-2 space-y-6">
            {/* Current Slot Info */}
            {currentSlot && (
              <CurrentSlot
                slot={currentSlot}
                slotIndex={currentSlotIndex!}
                exercise={currentExercise}
                loadingExercise={loadingExercise}
              />
            )}

            {/* Exercise Panel */}
            {currentSlot && currentExercise && (
              <ExercisePanel exercise={currentExercise} />
            )}

            {/* Set Tracker */}
            {currentSlot && (
              <SetTracker
                slotIndex={currentSlotIndex!}
                slot={currentSlot}
                exercise={currentExercise}
              />
            )}
          </div>

          {/* Right Column: Rest Timer & Controls */}
          <div className="space-y-6">
            {/* Rest Timer */}
            {currentSlot && currentSlot.slotState === 'in_progress' && (
              <RestTimer
                externalControl={{
                  isRunning: restTimerRunning,
                  onToggle: (isRunning) => setRestTimerRunning(isRunning),
                }}
              />
            )}

            {/* Workout Controls */}
            <WorkoutControls
              workoutState={activeWorkout.state}
              onPause={pauseWorkout}
              onResume={resumeWorkout}
              onComplete={completeWorkout}
              onAbandon={abandonWorkout}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
