/**
 * Routine Designer Page
 * Main interface for creating and editing workout routines
 */
import { useState } from 'react'
import { useRoutineStore } from '../stores/routineStore'
import SlotEditor from '../components/SlotEditor'
import SlotList from '../components/SlotList'
import RoutineHeader from '../components/RoutineHeader'

export default function RoutineDesigner() {
  const { currentRoutine, setCurrentRoutine } = useRoutineStore()
  const [selectedSlotId, setSelectedSlotId] = useState<string | null>(null)

  const handleNewRoutine = () => {
    setCurrentRoutine({
      name: 'New Routine',
      routineType: 'custom',
      workoutStyle: 'custom',
      description: '',
      slots: [],
    })
  }

  const selectedSlot = currentRoutine?.slots.find((s) => s.id === selectedSlotId)

  return (
    <div className="routine-designer">
      <div className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">Routine Designer</h1>

        {!currentRoutine ? (
          <div className="text-center py-12">
            <p className="text-gray-600 mb-4">No routine loaded</p>
            <button
              onClick={handleNewRoutine}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Create New Routine
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Routine Header and Slot List */}
            <div className="lg:col-span-1 space-y-4">
              <RoutineHeader />
              <SlotList
                selectedSlotId={selectedSlotId}
                onSelectSlot={setSelectedSlotId}
              />
            </div>

            {/* Right: Slot Editor */}
            <div className="lg:col-span-2">
              {selectedSlot ? (
                <SlotEditor slot={selectedSlot} />
              ) : (
                <div className="bg-gray-50 rounded-lg p-8 text-center text-gray-500">
                  Select a slot to edit, or create a new slot
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
