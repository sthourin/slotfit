/**
 * Current Slot Component
 * Displays information about the current slot being worked on
 */
import { type ActiveWorkoutSlot } from '../../stores/workoutStore'
import { type Exercise } from '../../services/exercises'
import { useWorkoutStore } from '../../stores/workoutStore'
import { useUIStore } from '../../stores/uiStore'
import ExerciseSelector from './ExerciseSelector'

interface CurrentSlotProps {
  slot: ActiveWorkoutSlot
  slotIndex: number
  exercise: Exercise | null
  loadingExercise: boolean
}

export default function CurrentSlot({
  slot,
  slotIndex,
  exercise,
  loadingExercise,
}: CurrentSlotProps) {
  const { startSlot, completeSlot, skipSlot } = useWorkoutStore()
  const { openModal } = useUIStore()

  const handleSelectExercise = () => {
    openModal('exerciseSelector', { slotIndex, muscleGroupIds: slot.muscleGroupIds, slotId: slot.slotId })
  }

  const handleStart = () => {
    startSlot(slotIndex)
  }

  const handleComplete = () => {
    completeSlot(slotIndex)
  }

  const handleSkip = () => {
    if (window.confirm('Are you sure you want to skip this slot?')) {
      skipSlot(slotIndex)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h2 className="text-2xl font-bold mb-2">
            Slot {slotIndex + 1}
            {slot.slotState === 'in_progress' && (
              <span className="ml-2 text-sm font-normal text-blue-600">
                (In Progress)
              </span>
            )}
            {slot.slotState === 'completed' && (
              <span className="ml-2 text-sm font-normal text-green-600">
                (Completed)
              </span>
            )}
          </h2>

          {loadingExercise ? (
            <div className="text-gray-500">Loading exercise...</div>
          ) : exercise ? (
            <div>
              <h3 className="text-xl font-semibold text-gray-900">
                {exercise.name}
              </h3>
              {exercise.difficulty && (
                <span className="inline-block mt-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                  {exercise.difficulty}
                </span>
              )}
            </div>
          ) : slot.exerciseName ? (
            <div>
              <h3 className="text-xl font-semibold text-gray-900">
                {slot.exerciseName}
              </h3>
            </div>
          ) : (
            <div className="text-gray-500 italic">
              No exercise selected yet
            </div>
          )}
        </div>

        {/* Slot Actions */}
        <div className="flex gap-2">
          {slot.slotState === 'not_started' && (
            <>
              {!slot.exerciseId && (
                <button
                  onClick={handleSelectExercise}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                >
                  Select Exercise
                </button>
              )}
              {slot.exerciseId && (
                <button
                  onClick={handleStart}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Start Slot
                </button>
              )}
              <button
                onClick={handleSkip}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Skip
              </button>
            </>
          )}
          {slot.slotState === 'in_progress' && (
            <>
              <button
                onClick={handleSelectExercise}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                Change Exercise
              </button>
              <button
                onClick={handleComplete}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Complete Slot
              </button>
            </>
          )}
        </div>
      </div>

      {/* Sets Summary */}
      {slot.sets.length > 0 && (
        <div className="mt-4 pt-4 border-t">
          <div className="text-sm text-gray-600">
            <strong>{slot.sets.length}</strong> set{slot.sets.length !== 1 ? 's' : ''} logged
          </div>
        </div>
      )}

      {/* Exercise Selector Modal */}
      <ExerciseSelector
        slotIndex={slotIndex}
        muscleGroupIds={slot.muscleGroupIds}
        slotId={slot.slotId}
      />
    </div>
  )
}
