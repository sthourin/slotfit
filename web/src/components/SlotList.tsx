/**
 * Slot List Component
 * Displays all slots in the routine with drag-and-drop reordering
 */
import { useRoutineStore } from '../stores/routineStore'

interface SlotListProps {
  selectedSlotId: string | null
  onSelectSlot: (slotId: string) => void
}

export default function SlotList({ selectedSlotId, onSelectSlot }: SlotListProps) {
  const { currentRoutine, addSlot, removeSlot } = useRoutineStore()

  if (!currentRoutine) return null

  const handleAddSlot = () => {
    addSlot({
      name: null,
      order: currentRoutine.slots.length + 1,
      muscleGroupIds: [],
      supersetTag: null,
      selectedExerciseId: null,
      workoutStyle: null,
    })
  }

  const handleRemoveSlot = (slotId: string) => {
    if (confirm('Remove this slot?')) {
      removeSlot(slotId)
      if (selectedSlotId === slotId) {
        onSelectSlot('')
      }
    }
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b flex justify-between items-center">
        <h3 className="font-semibold">Slots ({currentRoutine.slots.length})</h3>
        <button
          onClick={handleAddSlot}
          className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          + Add Slot
        </button>
      </div>

      <div className="divide-y">
        {currentRoutine.slots.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            No slots yet. Add a slot to get started.
          </div>
        ) : (
          currentRoutine.slots
            .sort((a, b) => a.order - b.order)
            .map((slot) => (
              <div
                key={slot.id}
                onClick={() => onSelectSlot(slot.id)}
                className={`p-3 cursor-pointer hover:bg-gray-50 ${
                  selectedSlotId === slot.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="font-medium text-sm">
                      {slot.name || `Slot ${slot.order}`}
                      {slot.supersetTag && (
                        <span className="ml-2 px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">
                          Superset: {slot.supersetTag}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {slot.muscleGroupIds.length > 0
                        ? `${slot.muscleGroupIds.length} muscle group(s)`
                        : 'No muscle groups selected'}
                      {slot.workoutStyle && (
                        <span className="ml-2 px-1.5 py-0.5 text-xs bg-green-100 text-green-700 rounded">
                          {slot.workoutStyle}
                        </span>
                      )}
                      {slot.selectedExerciseId && (
                        <span className="ml-2 text-blue-600">• Exercise selected</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRemoveSlot(slot.id)
                    }}
                    className="text-red-500 hover:text-red-700 text-sm"
                  >
                    ×
                  </button>
                </div>
              </div>
            ))
        )}
      </div>
    </div>
  )
}
