/**
 * Slot Progress Bar Component
 * Shows all slots with their status and type, clickable to navigate
 */
import { type ActiveWorkoutSlot, type SlotType } from '../../stores/workoutStore'

interface SlotProgressBarProps {
  slots: ActiveWorkoutSlot[]
  currentSlotIndex: number | null
  onSelectSlot: (index: number) => void
}

// Slot type visual configuration
const SLOT_TYPE_STYLES: Record<SlotType, { bg: string; border: string; label: string }> = {
  standard: {
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    label: '',
  },
  warmup: {
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    label: 'W',
  },
  finisher: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    label: 'F',
  },
  active_recovery: {
    bg: 'bg-teal-50',
    border: 'border-teal-200',
    label: 'R',
  },
  wildcard: {
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    label: '*',
  },
}

export default function SlotProgressBar({
  slots,
  currentSlotIndex,
  onSelectSlot,
}: SlotProgressBarProps) {
  const getSlotStatusIndicator = (slot: ActiveWorkoutSlot) => {
    switch (slot.slotState) {
      case 'completed':
        return { icon: '✓', color: 'text-green-600' }
      case 'in_progress':
        return { icon: '●', color: 'text-blue-600' }
      case 'skipped':
        return { icon: '—', color: 'text-gray-400' }
      case 'not_started':
      default:
        return { icon: '○', color: 'text-gray-400' }
    }
  }

  const getSlotStatusBg = (slot: ActiveWorkoutSlot) => {
    switch (slot.slotState) {
      case 'completed':
        return 'bg-green-100'
      case 'in_progress':
        return 'bg-blue-100'
      case 'skipped':
        return 'bg-gray-200'
      case 'not_started':
      default:
        return ''
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

      {/* Slot Buttons with Type Indicators */}
      <div className="flex flex-wrap gap-2">
        {slots.map((slot, index) => {
          const isCurrent = currentSlotIndex === index
          const hasExercise = slot.exerciseId !== null
          const slotType = slot.slotType || 'standard'
          const typeStyle = SLOT_TYPE_STYLES[slotType] || SLOT_TYPE_STYLES.standard
          const statusIndicator = getSlotStatusIndicator(slot)
          const statusBg = getSlotStatusBg(slot)

          return (
            <button
              key={index}
              onClick={() => onSelectSlot(index)}
              className={`
                relative px-3 py-2 rounded-lg border-2 transition-all min-w-[56px]
                ${isCurrent ? 'border-blue-600 ring-2 ring-blue-200 scale-105' : typeStyle.border}
                ${statusBg || typeStyle.bg}
                hover:scale-102 hover:shadow-sm
              `}
              title={
                slot.exerciseName
                  ? `Slot ${index + 1}${slot.slotName ? ` - ${slot.slotName}` : ''}: ${slot.exerciseName}`
                  : `Slot ${index + 1}${slot.slotName ? ` - ${slot.slotName}` : ''}`
              }
            >
              {/* Slot Type Badge (top-left) */}
              {typeStyle.label && (
                <span
                  className={`
                    absolute -top-1 -left-1 w-4 h-4 text-xs font-bold rounded-full
                    flex items-center justify-center border border-white
                    ${slotType === 'warmup' ? 'bg-orange-400 text-white' : ''}
                    ${slotType === 'finisher' ? 'bg-red-400 text-white' : ''}
                    ${slotType === 'active_recovery' ? 'bg-teal-400 text-white' : ''}
                    ${slotType === 'wildcard' ? 'bg-purple-400 text-white' : ''}
                  `}
                >
                  {typeStyle.label}
                </span>
              )}

              {/* Main Content */}
              <div className="flex items-center gap-1.5">
                <span className="text-lg font-semibold text-gray-900">{index + 1}</span>
                <span className={`text-sm ${statusIndicator.color}`}>
                  {statusIndicator.icon}
                </span>
              </div>

              {/* No Exercise Warning (top-right) */}
              {!hasExercise && slot.slotState !== 'skipped' && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-yellow-400 rounded-full border-2 border-white" />
              )}

              {/* Current Slot Indicator (bottom) */}
              {isCurrent && (
                <span className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-blue-600 rounded-full" />
              )}
            </button>
          )
        })}
      </div>

      {/* Legend for slot types (show if there are non-standard types) */}
      {slots.some((s) => s.slotType && s.slotType !== 'standard') && (
        <div className="mt-3 pt-3 border-t border-gray-100 flex flex-wrap gap-3 text-xs text-gray-500">
          {slots.some((s) => s.slotType === 'warmup') && (
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-orange-400 rounded-full"></span> Warmup
            </span>
          )}
          {slots.some((s) => s.slotType === 'finisher') && (
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-red-400 rounded-full"></span> Finisher
            </span>
          )}
          {slots.some((s) => s.slotType === 'active_recovery') && (
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-teal-400 rounded-full"></span> Recovery
            </span>
          )}
          {slots.some((s) => s.slotType === 'wildcard') && (
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-purple-400 rounded-full"></span> Wildcard
            </span>
          )}
        </div>
      )}
    </div>
  )
}
