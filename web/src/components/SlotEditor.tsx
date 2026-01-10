/**
 * Slot Editor Component
 * Edit slot muscle group scope and superset tags
 */
import { useState, useEffect, useMemo } from 'react'
import { useRoutineStore } from '../stores/routineStore'
import { muscleGroupApi, MuscleGroup } from '../services/muscleGroups'
import { exerciseApi, Exercise } from '../services/exercises'
import MuscleGroupSelector from './MuscleGroupSelector'
import ExerciseList from './ExerciseList'
import CreateVariantDialog from './CreateVariantDialog'

interface SlotEditorProps {
  slot: {
    id: string
    name: string | null
    order: number
    muscleGroupIds: number[]
    supersetTag: string | null
    selectedExerciseId: number | null
    workoutStyle: string | null  // Optional workout style for this slot
  }
}

export default function SlotEditor({ slot }: SlotEditorProps) {
  const { currentRoutine, updateSlot, setSlotSupersetTag } = useRoutineStore()
  const [allMuscleGroups, setAllMuscleGroups] = useState<MuscleGroup[]>([])
  const [loadingMuscleGroups, setLoadingMuscleGroups] = useState(true)
  const [slotNameInput, setSlotNameInput] = useState(slot.name || '')
  const [supersetTagInput, setSupersetTagInput] = useState(slot.supersetTag || '')
  const [workoutStyleInput, setWorkoutStyleInput] = useState(slot.workoutStyle || '')
  const [filteredExercises, setFilteredExercises] = useState<Exercise[]>([])
  const [loadingExercises, setLoadingExercises] = useState(false)
  const [showVariantDialog, setShowVariantDialog] = useState(false)
  const [selectedExerciseForVariant, setSelectedExerciseForVariant] = useState<Exercise | null>(null)
  const [filterByRoutineType, setFilterByRoutineType] = useState(true) // Default to filtering enabled

  const WORKOUT_STYLES = ['5x5', 'HIIT', 'volume', 'strength', 'custom']

  // Filter muscle groups based on routine type (anterior/posterior) if filter is enabled
  const muscleGroups = useMemo(() => {
    // If filter is disabled, show all muscle groups
    if (!filterByRoutineType) {
      return allMuscleGroups
    }

    // If no routine type or custom/full_body, show all
    if (!currentRoutine?.routineType || currentRoutine.routineType === 'custom' || currentRoutine.routineType === 'full_body') {
      return allMuscleGroups
    }

    // Define anterior and posterior muscle groups (matching backend logic)
    const anteriorGroups = ['Chest', 'Shoulders', 'Quadriceps', 'Abdominals', 'Biceps']
    const posteriorGroups = ['Back', 'Hamstrings', 'Glutes', 'Triceps', 'Calves']

    const targetGroups = currentRoutine.routineType === 'anterior' ? anteriorGroups : posteriorGroups

    // Filter to only show level 1 muscle groups that match the routine type
    // Also include their children (levels 2-4) if the parent matches
    const filtered = allMuscleGroups.filter(mg => {
      if (mg.level === 1) {
        // Level 1: Check if name matches
        return targetGroups.includes(mg.name)
      } else {
        // Level 2-4: Check if any ancestor is in target groups
        // We need to find the root level 1 ancestor
        const findRoot = (mgId: number | null, visited = new Set<number>()): MuscleGroup | null => {
          if (!mgId || visited.has(mgId)) return null
          visited.add(mgId)
          const mg = allMuscleGroups.find(m => m.id === mgId)
          if (!mg) return null
          if (mg.level === 1) return mg
          return findRoot(mg.parent_id, visited)
        }
        const root = findRoot(mg.parent_id)
        return root && targetGroups.includes(root.name)
      }
    })

    return filtered
  }, [allMuscleGroups, currentRoutine?.routineType, filterByRoutineType])

  useEffect(() => {
    loadMuscleGroups()
  }, [])

  useEffect(() => {
    setSlotNameInput(slot.name || '')
  }, [slot.name])

  useEffect(() => {
    setSupersetTagInput(slot.supersetTag || '')
  }, [slot.supersetTag])

  useEffect(() => {
    setWorkoutStyleInput(slot.workoutStyle || '')
  }, [slot.workoutStyle])

  useEffect(() => {
    if (slot.muscleGroupIds.length > 0) {
      loadFilteredExercises()
    } else {
      setFilteredExercises([])
    }
  }, [slot.muscleGroupIds, slot.workoutStyle, currentRoutine?.routineType, currentRoutine?.workoutStyle])

  const loadMuscleGroups = async () => {
    setLoadingMuscleGroups(true)
    try {
      const groups = await muscleGroupApi.list()
      setAllMuscleGroups(groups)
    } catch (error) {
      console.error('Failed to load muscle groups:', error)
    } finally {
      setLoadingMuscleGroups(false)
    }
  }

  const handleMuscleGroupsChange = (selectedIds: number[]) => {
    updateSlot(slot.id, { muscleGroupIds: selectedIds })
  }

  const handleSlotNameChange = (name: string) => {
    setSlotNameInput(name)
    updateSlot(slot.id, { name: name || null })
  }

  const handleSupersetTagChange = (tag: string) => {
    setSupersetTagInput(tag)
    setSlotSupersetTag(slot.id, tag || null)
  }

  const handleWorkoutStyleChange = (style: string) => {
    setWorkoutStyleInput(style)
    updateSlot(slot.id, { workoutStyle: style || null })
  }

  const loadFilteredExercises = async () => {
    if (slot.muscleGroupIds.length === 0) return
    
    setLoadingExercises(true)
    try {
      // Get exercises filtered by all selected muscle groups
      // Also filter by routine type and workout style if set
      const params: Parameters<typeof exerciseApi.list>[0] = {
        limit: 200,  // Get more exercises for client-side filtering
        muscle_group_ids: slot.muscleGroupIds,
      }
      
      // Add routine type filtering if set
      if (currentRoutine?.routineType && currentRoutine.routineType !== 'custom' && currentRoutine.routineType !== 'full_body') {
        params.routine_type = currentRoutine.routineType
      }
      
      // Use slot's workout_style if set, otherwise fall back to routine's workout_style
      const effectiveWorkoutStyle = slot.workoutStyle || currentRoutine?.workoutStyle
      
      // Add workout style filtering if set
      if (effectiveWorkoutStyle && effectiveWorkoutStyle !== 'custom') {
        params.workout_style = effectiveWorkoutStyle
        // Include variants so users can see and select matching variants
        // But don't filter by variant_type - we want to show BOTH base exercises AND variants
        // The variant_type filter would exclude base exercises, which we don't want
        params.include_variants = true
      } else {
        // For custom routines, show base exercises only (exclude variants)
        params.include_variants = false
      }
      
      const response = await exerciseApi.list(params)
      setFilteredExercises(response.exercises)
    } catch (error) {
      console.error('Failed to load exercises:', error)
    } finally {
      setLoadingExercises(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">
        {slot.name || `Edit Slot ${slot.order}`}
      </h2>

      <div className="space-y-6">
        {/* Slot Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Slot Name (Optional)
          </label>
          <p className="text-xs text-gray-500 mb-2">
            Give this slot a descriptive name (e.g., "Warm-up", "Main Set 1", "Cool-down")
          </p>
          <input
            type="text"
            value={slotNameInput}
            onChange={(e) => handleSlotNameChange(e.target.value)}
            placeholder={`Slot ${slot.order}`}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Muscle Group Selection */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">
              Muscle Group Scope
            </label>
            {currentRoutine?.routineType && 
             currentRoutine.routineType !== 'custom' && 
             currentRoutine.routineType !== 'full_body' && (
              <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filterByRoutineType}
                  onChange={(e) => setFilterByRoutineType(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span>Filter by {currentRoutine.routineType} routine</span>
              </label>
            )}
          </div>
          <p className="text-xs text-gray-500 mb-3">
            Select which muscle groups this slot targets. Exercises will be filtered by these groups.
            {filterByRoutineType && currentRoutine?.routineType && 
             currentRoutine.routineType !== 'custom' && 
             currentRoutine.routineType !== 'full_body' && (
              <span className="ml-1 text-blue-600">
                (Filtered to {currentRoutine.routineType} muscle groups)
              </span>
            )}
          </p>
          {loadingMuscleGroups ? (
            <div className="border border-gray-300 rounded-md p-4 text-center text-gray-500">
              Loading muscle groups...
            </div>
          ) : muscleGroups.length === 0 ? (
            <div className="border border-gray-300 rounded-md p-4 text-center text-gray-500">
              No muscle groups available. Please check your connection.
            </div>
          ) : (
            <MuscleGroupSelector
              muscleGroups={muscleGroups}
              selectedIds={slot.muscleGroupIds || []}
              onChange={handleMuscleGroupsChange}
            />
          )}
        </div>

        {/* Superset Tag */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Superset Tag (Optional)
          </label>
          <p className="text-xs text-gray-500 mb-2">
            Slots with the same tag will be grouped as a superset during workouts.
          </p>
          <input
            type="text"
            value={supersetTagInput}
            onChange={(e) => handleSupersetTagChange(e.target.value)}
            placeholder="e.g., 'A', 'Upper', 'Push'"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {supersetTagInput && (
            <p className="text-xs text-gray-500 mt-1">
              This slot will be part of superset: <strong>{supersetTagInput}</strong>
            </p>
          )}
        </div>

        {/* Workout Style */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Workout Style (Optional)
          </label>
          <p className="text-xs text-gray-500 mb-2">
            Set a workout style for this slot to filter exercises. If not set, uses the routine's workout style.
          </p>
          <select
            value={workoutStyleInput}
            onChange={(e) => handleWorkoutStyleChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Use Routine Default ({currentRoutine?.workoutStyle || 'None'})</option>
            {WORKOUT_STYLES.map(style => (
              <option key={style} value={style}>{style}</option>
            ))}
          </select>
          {workoutStyleInput && (
            <p className="text-xs text-gray-500 mt-1">
              This slot will filter exercises for: <strong>{workoutStyleInput}</strong>
            </p>
          )}
        </div>

        {/* Exercise Recommendations */}
        {slot.muscleGroupIds.length > 0 && (
          <div className="border-t pt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">
              Exercises for This Slot ({filteredExercises.length})
            </h3>
            <p className="text-xs text-gray-500 mb-3">
              Exercises filtered by selected muscle groups
            </p>
            {loadingExercises ? (
              <div className="text-center py-4 text-gray-500">Loading exercises...</div>
            ) : (
              <>
                <ExerciseList
                  exercises={filteredExercises}
                  muscleGroupIds={slot.muscleGroupIds}
                  selectedExerciseId={slot.selectedExerciseId}
                  onSelectExercise={(exerciseId) => {
                    updateSlot(slot.id, { selectedExerciseId: exerciseId })
                  }}
                  onCreateVariant={(exercise) => {
                    setSelectedExerciseForVariant(exercise)
                    setShowVariantDialog(true)
                  }}
                />
                {showVariantDialog && selectedExerciseForVariant && (
                  <CreateVariantDialog
                    exercise={selectedExerciseForVariant}
                    workoutStyle={slot.workoutStyle || currentRoutine?.workoutStyle}
                    onClose={() => {
                      setShowVariantDialog(false)
                      setSelectedExerciseForVariant(null)
                    }}
                    onCreated={() => {
                      setShowVariantDialog(false)
                      setSelectedExerciseForVariant(null)
                      // Reload exercises to show the new variant
                      loadFilteredExercises()
                    }}
                  />
                )}
              </>
            )}
          </div>
        )}

        {/* Preview */}
        <div className="border-t pt-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Slot Preview</h3>
          <div className="bg-gray-50 rounded p-3 text-sm">
            <div className="space-y-1">
              {slot.name && (
                <div>
                  <strong>Name:</strong> {slot.name}
                </div>
              )}
              <div>
                <strong>Order:</strong> {slot.order}
              </div>
              <div>
                <strong>Muscle Groups:</strong>{' '}
                {slot.muscleGroupIds.length > 0
                  ? slot.muscleGroupIds
                      .map((id) => {
                        const mg = allMuscleGroups.find((g) => g.id === id)
                        return mg?.name || `ID: ${id}`
                      })
                      .join(', ')
                  : 'None selected'}
              </div>
              {slot.workoutStyle && (
                <div>
                  <strong>Workout Style:</strong> {slot.workoutStyle}
                </div>
              )}
              {slot.supersetTag && (
                <div>
                  <strong>Superset:</strong> {slot.supersetTag}
                </div>
              )}
              {slot.selectedExerciseId && (
                <div>
                  <strong>Selected Exercise:</strong>{' '}
                  {filteredExercises.find((e) => e.id === slot.selectedExerciseId)?.name || 
                   `Exercise ID: ${slot.selectedExerciseId}`}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
