/**
 * Slot Progress Bar Component
 * Shows all slots with their status, clickable to navigate
 */
import { type ActiveWorkoutSlot } from '../../stores/workoutStore'

interface SlotProgressBarProps {
  slots: ActiveWorkoutSlot[]
  currentSlotIndex: number | null
  onSelectSlot: (index: number) => void
}

export default function SlotProgressBar({
  slots,
  currentSlotIndex,
  onSelectSlot,
}: SlotProgressBarProps) {
  const getSlotStatusColor = (slot: ActiveWorkoutSlot) => {
    switch (slot.slotState) {
      case 'completed':
        return 'bg-green-500'
      case 'in_progress':
        return 'bg-blue-500'
      case 'skipped':
        return 'bg-gray-400'
      case 'not_started':
      default:
        return 'bg-gray-300'
    }
  }

  const getSlotStatusText = (slot: ActiveWorkoutSlot) => {
    switch (slot.slotState) {
      case 'completed':
        return '✓'
      case 'in_progress':
        return '●'
      case 'skipped':
        return '—'
      case 'not_started':
      default:
        return '○'
    }
  }

  if (slots.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-4">
        <p className="text-gray-500 text-center">No slots in this workout</p>
      </div>
    )
  }

  const completedCount = slots.filter((s) => s.slotState === 'completed').length
  const progressPercentage = (completedCount / slots.length) * 100

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      {/* Progress Summary */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            Progress: {completedCount} / {slots.length} slots
          </span>
          <span className="text-sm text-gray-600">
            {Math.round(progressPercentage)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Slot Buttons */}
      <div className="flex flex-wrap gap-2">
        {slots.map((slot, index) => {
          const isCurrent = currentSlotIndex === index
          const hasExercise = slot.exerciseId !== null

          return (
            <button
              key={index}
              onClick={() => onSelectSlot(index)}
              className={`
                relative px-4 py-2 rounded-lg border-2 transition-all
                ${isCurrent ? 'border-blue-600 bg-blue-50 scale-105' : 'border-gray-200 hover:border-gray-300'}
                ${getSlotStatusColor(slot)} bg-opacity-10
              `}
              title={
                slot.exerciseName
                  ? `Slot ${index + 1}: ${slot.exerciseName}`
                  : `Slot ${index + 1}`
              }
            >
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold">{index + 1}</span>
                <span className="text-xs">{getSlotStatusText(slot)}</span>
              </div>
              {!hasExercise && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-yellow-400 rounded-full border-2 border-white" />
              )}
              {isCurrent && (
                <span className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-blue-600 rounded-full" />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
