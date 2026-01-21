/**
 * Set Tracker Component
 * For logging sets (reps, weight, rest)
 */
import { useState, useEffect, useCallback, useRef, type DragEvent } from 'react'
import { type ActiveWorkoutSlot } from '../../stores/workoutStore'
import { type Exercise } from '../../services/exercises'
import { useWorkoutStore } from '../../stores/workoutStore'
import { type WorkoutSet } from '../../services/workouts'

interface SetTrackerProps {
  slotIndex: number
  slot: ActiveWorkoutSlot
  exercise: Exercise | null
}

export default function SetTracker({
  slotIndex,
  slot,
  exercise,
}: SetTrackerProps) {
  const { addSet, updateSet, removeSet, reorderSets } = useWorkoutStore()
  const [editingSetIndex, setEditingSetIndex] = useState<number | null>(null)
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)
  const previousSlotStateRef = useRef<ActiveWorkoutSlot['slotState']>(slot.slotState)

  // Default values from exercise variant
  const defaultReps = exercise?.default_reps || null
  const defaultWeight = exercise?.default_weight || null
  const defaultRest = exercise?.default_rest_seconds || null

  const handleAddSet = useCallback(() => {
    const setNumber = slot.sets.length + 1
    addSet(slotIndex, {
      set_number: setNumber,
      reps: defaultReps,
      weight: defaultWeight,
      rest_seconds: defaultRest,
      rpe: null,
      notes: null,
    })
    setEditingSetIndex(setNumber - 1)
  }, [slotIndex, slot.sets.length, defaultReps, defaultWeight, defaultRest, addSet])

  useEffect(() => {
    const previousSlotState = previousSlotStateRef.current
    previousSlotStateRef.current = slot.slotState
    if (
      previousSlotState !== 'in_progress' &&
      slot.slotState === 'in_progress' &&
      slot.sets.length === 0
    ) {
      handleAddSet()
    }
  }, [slot.slotState, slot.sets.length, handleAddSet])
  
  // Expose addSet function for keyboard shortcuts
  useEffect(() => {
    if (slot.slotState === 'in_progress') {
      (window as Record<string, unknown>).__setTrackerAddSet = handleAddSet
    }
    return () => {
      delete (window as any).__setTrackerAddSet
    }
  }, [handleAddSet, slot.slotState])

  const handleUpdateSet = (
    setIndex: number,
    updates: Partial<WorkoutSet>
  ) => {
    updateSet(slotIndex, setIndex, updates)
    setEditingSetIndex(null)
  }

  const handleSaveAndAddSet = (
    setIndex: number,
    updates: Partial<WorkoutSet>
  ) => {
    updateSet(slotIndex, setIndex, updates)
    handleAddSet()
  }

  const handleRemoveSet = (setIndex: number) => {
    if (window.confirm('Remove this set?')) {
      removeSet(slotIndex, setIndex)
    }
  }

  const canReorder = slot.slotState === 'in_progress'

  const handleDragStart = useCallback(
    (setIndex: number) => (event: DragEvent<HTMLDivElement>) => {
      if (!canReorder) return
      setDraggingIndex(setIndex)
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/plain', String(setIndex))
    },
    [canReorder]
  )

  const handleDragOver = useCallback(
    (setIndex: number) => (event: DragEvent<HTMLDivElement>) => {
      if (!canReorder) return
      event.preventDefault()
      setDragOverIndex(setIndex)
      event.dataTransfer.dropEffect = 'move'
    },
    [canReorder]
  )

  const handleDrop = useCallback(
    (setIndex: number) => (event: DragEvent<HTMLDivElement>) => {
      if (!canReorder) return
      event.preventDefault()
      const dataIndex = parseInt(event.dataTransfer.getData('text/plain'), 10)
      const fromIndex = Number.isNaN(dataIndex) ? draggingIndex : dataIndex
      if (fromIndex === null || fromIndex === setIndex || !slot.sets[fromIndex]) {
        setDraggingIndex(null)
        setDragOverIndex(null)
        return
      }

      const reorderedSets = [...slot.sets]
      const [movedSet] = reorderedSets.splice(fromIndex, 1)
      reorderedSets.splice(setIndex, 0, movedSet)
      reorderSets(slotIndex, reorderedSets.map((workoutSet) => workoutSet.id))
      setDraggingIndex(null)
      setDragOverIndex(null)
    },
    [canReorder, draggingIndex, slot.sets, slotIndex, reorderSets]
  )

  const handleDragEnd = useCallback(() => {
    setDraggingIndex(null)
    setDragOverIndex(null)
  }, [])

  const startEditing = (setIndex: number) => {
    setEditingSetIndex(setIndex)
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold">Sets</h3>
        {slot.slotState === 'in_progress' && (
          <button
            onClick={handleAddSet}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            + Add Set
          </button>
        )}
      </div>

      {slot.sets.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No sets logged yet</p>
          {slot.slotState === 'in_progress' && (
            <p className="text-sm mt-2">Click "Add Set" to start logging</p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {slot.sets.map((set, setIndex) => {
            const isEditing = editingSetIndex === setIndex
            const isDragging = draggingIndex === setIndex
            const isDragOver = dragOverIndex === setIndex

            return (
              <div
                key={setIndex}
                className={`border rounded-lg p-4 transition-colors ${
                  isDragging ? 'opacity-60' : 'hover:bg-gray-50'
                } ${isDragOver ? 'border-blue-400 bg-blue-50' : ''}`}
                draggable={canReorder}
                onDragStart={handleDragStart(setIndex)}
                onDragOver={handleDragOver(setIndex)}
                onDrop={handleDrop(setIndex)}
                onDragEnd={handleDragEnd}
              >
                {isEditing ? (
                  <SetEditForm
                    set={set}
                    onSave={(updates) => handleUpdateSet(setIndex, updates)}
                    onSaveAndAdd={(updates) => handleSaveAndAddSet(setIndex, updates)}
                    onCancel={() => setEditingSetIndex(null)}
                  />
                ) : (
                  <SetDisplay
                    set={set}
                    setNumber={set.set_number}
                    onEdit={() => startEditing(setIndex)}
                    onRemove={() => handleRemoveSet(setIndex)}
                    canEdit={slot.slotState === 'in_progress'}
                    canReorder={canReorder}
                  />
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

interface SetDisplayProps {
  set: WorkoutSet
  setNumber: number
  onEdit: () => void
  onRemove: () => void
  canEdit: boolean
  canReorder: boolean
}

function SetDisplay({
  set,
  setNumber,
  onEdit,
  onRemove,
  canEdit,
  canReorder,
}: SetDisplayProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3 flex-1">
        {canReorder && (
          <div
            className="text-gray-400 cursor-grab select-none"
            title="Drag to reorder"
          >
            ⠿
          </div>
        )}
        <div className="flex-1 grid grid-cols-5 gap-4">
        <div>
          <div className="text-xs text-gray-500">Set</div>
          <div className="font-semibold">{setNumber}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Reps</div>
          <div className="font-medium">{set.reps ?? '—'}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Weight</div>
          <div className="font-medium">
            {set.weight ? `${set.weight} lbs` : '—'}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500">RPE</div>
          <div className="font-medium">{set.rpe ?? '—'}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Rest</div>
          <div className="font-medium">
            {set.rest_seconds
              ? `${Math.floor(set.rest_seconds / 60)}:${String(set.rest_seconds % 60).padStart(2, '0')}`
              : '—'}
          </div>
        </div>
      </div>
      </div>
      {canEdit && (
        <div className="flex gap-2 ml-4">
          <button
            onClick={onEdit}
            className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700"
          >
            Edit
          </button>
          <button
            onClick={onRemove}
            className="px-3 py-1 text-sm text-red-600 hover:text-red-700"
          >
            Remove
          </button>
        </div>
      )}
    </div>
  )
}

interface SetEditFormProps {
  set: WorkoutSet
  onSave: (updates: Partial<WorkoutSet>) => void
  onSaveAndAdd: (updates: Partial<WorkoutSet>) => void
  onCancel: () => void
}

function SetEditForm({ set, onSave, onSaveAndAdd, onCancel }: SetEditFormProps) {
  const repsInputRef = useRef<HTMLInputElement | null>(null)
  const [reps, setReps] = useState<string>(set.reps?.toString() || '')
  const [weight, setWeight] = useState<string>(set.weight?.toString() || '')
  const [rpe, setRpe] = useState<string>(set.rpe?.toString() || '')
  const [restMinutes, setRestMinutes] = useState<string>(
    set.rest_seconds ? Math.floor(set.rest_seconds / 60).toString() : ''
  )
  const [restSeconds, setRestSeconds] = useState<string>(
    set.rest_seconds ? (set.rest_seconds % 60).toString() : ''
  )

  useEffect(() => {
    repsInputRef.current?.focus()
  }, [set.id])

  const handleSave = () => {
    const restTotal =
      (parseInt(restMinutes) || 0) * 60 + (parseInt(restSeconds) || 0)
    onSave({
      reps: reps ? parseInt(reps) : null,
      weight: weight ? parseFloat(weight) : null,
      rpe: rpe ? parseFloat(rpe) : null,
      rest_seconds: restTotal > 0 ? restTotal : null,
    })
  }

  const handleSaveAndAdd = () => {
    const restTotal =
      (parseInt(restMinutes) || 0) * 60 + (parseInt(restSeconds) || 0)
    onSaveAndAdd({
      reps: reps ? parseInt(reps) : null,
      weight: weight ? parseFloat(weight) : null,
      rpe: rpe ? parseFloat(rpe) : null,
      rest_seconds: restTotal > 0 ? restTotal : null,
    })
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-4 gap-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Reps</label>
          <input
            type="number"
            ref={repsInputRef}
            value={reps}
            onChange={(e) => setReps(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg"
            placeholder="—"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Weight (lbs)</label>
          <input
            type="number"
            step="0.5"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg"
            placeholder="—"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">RPE (1-10)</label>
          <input
            type="number"
            step="0.5"
            min="1"
            max="10"
            value={rpe}
            onChange={(e) => setRpe(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg"
            placeholder="—"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Rest</label>
          <div className="flex gap-1">
            <input
              type="number"
              value={restMinutes}
              onChange={(e) => setRestMinutes(e.target.value)}
              className="w-full px-2 py-2 border rounded-lg"
              placeholder="min"
              min="0"
            />
            <span className="self-center">:</span>
            <input
              type="number"
              value={restSeconds}
              onChange={(e) => setRestSeconds(e.target.value)}
              className="w-full px-2 py-2 border rounded-lg"
              placeholder="sec"
              min="0"
              max="59"
            />
          </div>
        </div>
      </div>
      <div className="flex gap-2">
        <button
          onClick={handleSave}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
        >
          Save
        </button>
        <button
          onClick={handleSaveAndAdd}
          className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors text-sm"
        >
          Save and add set
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors text-sm"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
