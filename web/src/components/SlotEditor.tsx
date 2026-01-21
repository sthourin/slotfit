/**
 * Slot Editor Component
 * Edit slot muscle group scope and superset tags
 */
import { useState, useEffect, useMemo } from 'react'
import { useRoutineStore } from '../stores/routineStore'
import { muscleGroupApi, MuscleGroup } from '../services/muscleGroups'
import { exerciseApi, Exercise } from '../services/exercises'
import { apiClient } from '../services/api'
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
  const [combinationFilter, setCombinationFilter] = useState<string>('') // '', 'combination', 'single'
  const [secondaryMuscleGroupId, setSecondaryMuscleGroupId] = useState<number | null>(null)
  const [tertiaryMuscleGroupId, setTertiaryMuscleGroupId] = useState<number | null>(null)
  const [availableSecondaryGroups, setAvailableSecondaryGroups] = useState<MuscleGroup[]>([])
  const [availableTertiaryGroups, setAvailableTertiaryGroups] = useState<MuscleGroup[]>([])
  const [loadingAvailableGroups, setLoadingAvailableGroups] = useState(false)

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
      setAvailableSecondaryGroups([])
      setAvailableTertiaryGroups([])
    }
  }, [slot.muscleGroupIds, slot.workoutStyle, currentRoutine?.routineType, currentRoutine?.workoutStyle, combinationFilter, secondaryMuscleGroupId, tertiaryMuscleGroupId])

  // Load available secondary/tertiary muscle groups when filters change
  useEffect(() => {
    loadAvailableMuscleGroups()
    // Clear selected values when filters change (they may no longer be valid)
    setSecondaryMuscleGroupId(null)
    setTertiaryMuscleGroupId(null)
  }, [slot.muscleGroupIds, combinationFilter])

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
    if (slot.muscleGroupIds.length === 0) {
      setFilteredExercises([])
      return
    }
    
    setLoadingExercises(true)
    try {
      // Get exercises filtered by all selected muscle groups
      // Don't send routine_type when muscle groups are explicitly selected - 
      // the backend will use the explicit muscle groups with AND logic
      const params: Parameters<typeof exerciseApi.list>[0] = {
        limit: 200,  // Get more exercises for client-side filtering
        muscle_group_ids: slot.muscleGroupIds,
      }
      
      // Only add routine_type if no muscle groups are selected (for default filtering)
      // But since we require muscle groups to be selected, we don't send routine_type
      
      // Use slot's workout_style if set, otherwise fall back to routine's workout_style
      const effectiveWorkoutStyle = slot.workoutStyle || currentRoutine?.workoutStyle
      
      // Always include variants - users should see all available exercises
      // The variant filtering can be done client-side if needed
      params.include_variants = true
      
      // Only send workout_style if it's "HIIT" - the backend only supports HIIT filtering
      // Other workout styles (volume, strength, 5x5) don't have backend filtering yet
      if (effectiveWorkoutStyle && effectiveWorkoutStyle.toUpperCase() === 'HIIT') {
        params.workout_style = effectiveWorkoutStyle
      }
      
      // Add combination exercises filter if set
      if (combinationFilter === 'combination') {
        params.combination_only = true
      } else if (combinationFilter === 'single') {
        params.combination_only = false
      }
      
      // Add secondary and tertiary muscle group filters
      if (secondaryMuscleGroupId !== null) {
        params.secondary_muscle_group_ids = [secondaryMuscleGroupId]
      }
      if (tertiaryMuscleGroupId !== null) {
        params.tertiary_muscle_group_ids = [tertiaryMuscleGroupId]
      }
      
      console.log('Loading exercises with params:', JSON.stringify(params, null, 2))
      const response = await exerciseApi.list(params)
      console.log('Exercise API response:', { 
        total: response.total, 
        count: response.exercises.length,
        exercises: response.exercises.slice(0, 5).map(e => ({ id: e.id, name: e.name }))
      })
      setFilteredExercises(response.exercises)
      
      if (response.exercises.length === 0) {
        console.warn('No exercises found. Debugging info:')
        console.warn('Params sent:', params)
        console.warn('Total in response:', response.total)
        console.warn('Possible reasons:')
        console.warn('1. The muscle group filter requires ALL selected groups (AND logic)')
        console.warn('2. Try selecting fewer muscle groups or different combinations')
        console.warn('3. Check if workout_style filter is too restrictive')
        console.warn('4. Try testing without muscle group filter to see if exercises exist')
        
        // Test without muscle group filter to see if any exercises exist
        try {
          const testResponse = await exerciseApi.list({ limit: 5 })
          console.warn('Test query (no filters) returned:', testResponse.total, 'exercises')
        } catch (testError) {
          console.error('Test query failed:', testError)
        }
      }
    } catch (error) {
      console.error('Failed to load exercises:', error)
      setFilteredExercises([])
    } finally {
      setLoadingExercises(false)
    }
  }

  const loadAvailableMuscleGroups = async () => {
    if (slot.muscleGroupIds.length === 0) {
      setAvailableSecondaryGroups([])
      setAvailableTertiaryGroups([])
      return
    }

    setLoadingAvailableGroups(true)
    try {
      const baseParams: Record<string, any> = {
        muscle_group_ids: slot.muscleGroupIds.join(',')
      }
      if (combinationFilter === 'combination') {
        baseParams.combination_only = true
      } else if (combinationFilter === 'single') {
        baseParams.combination_only = false
      }

      // Load secondary groups
      const secondaryResponse = await apiClient.get('/exercises/available-muscle-groups', {
        params: { ...baseParams, role: 'secondary' }
      })
      setAvailableSecondaryGroups(secondaryResponse.data.muscle_groups || [])

      // Load tertiary groups
      const tertiaryResponse = await apiClient.get('/exercises/available-muscle-groups', {
        params: { ...baseParams, role: 'tertiary' }
      })
      setAvailableTertiaryGroups(tertiaryResponse.data.muscle_groups || [])
    } catch (error) {
      console.error('Failed to load available muscle groups:', error)
      setAvailableSecondaryGroups([])
      setAvailableTertiaryGroups([])
    } finally {
      setLoadingAvailableGroups(false)
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

        {/* Combination Exercises Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Exercise Type (Optional)
          </label>
          <p className="text-xs text-gray-500 mb-2">
            Filter exercises by whether they target single or multiple muscle groups.
          </p>
          <select
            value={combinationFilter}
            onChange={(e) => setCombinationFilter(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Exercises</option>
            <option value="combination">Combination Exercises Only</option>
            <option value="single">Single Muscle Group Only</option>
          </select>
          {combinationFilter && (
            <p className="text-xs text-gray-500 mt-1">
              Showing: <strong>{combinationFilter === 'combination' ? 'Combination exercises (multiple targets)' : 'Single muscle group exercises'}</strong>
            </p>
          )}
        </div>

        {/* Secondary Muscle Group Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Secondary Muscle Group (Optional)
          </label>
          <p className="text-xs text-gray-500 mb-2">
            Filter exercises that have this muscle group as a secondary target.
          </p>
          {loadingAvailableGroups ? (
            <div className="border border-gray-300 rounded-md p-4 text-center text-gray-500 text-sm">
              Loading available muscle groups...
            </div>
          ) : (
            <select
              value={secondaryMuscleGroupId || ''}
              onChange={(e) => setSecondaryMuscleGroupId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Secondary Muscle Groups</option>
              {availableSecondaryGroups.map((mg) => (
                <option key={mg.id} value={mg.id}>
                  {mg.name}
                </option>
              ))}
            </select>
          )}
          {secondaryMuscleGroupId && (
            <p className="text-xs text-gray-500 mt-1">
              Filtering by secondary muscle group: <strong>{availableSecondaryGroups.find(mg => mg.id === secondaryMuscleGroupId)?.name}</strong>
            </p>
          )}
        </div>

        {/* Tertiary Muscle Group Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tertiary Muscle Group (Optional)
          </label>
          <p className="text-xs text-gray-500 mb-2">
            Filter exercises that have this muscle group as a tertiary target.
          </p>
          {loadingAvailableGroups ? (
            <div className="border border-gray-300 rounded-md p-4 text-center text-gray-500 text-sm">
              Loading available muscle groups...
            </div>
          ) : (
            <select
              value={tertiaryMuscleGroupId || ''}
              onChange={(e) => setTertiaryMuscleGroupId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Tertiary Muscle Groups</option>
              {availableTertiaryGroups.map((mg) => (
                <option key={mg.id} value={mg.id}>
                  {mg.name}
                </option>
              ))}
            </select>
          )}
          {tertiaryMuscleGroupId && (
            <p className="text-xs text-gray-500 mt-1">
              Filtering by tertiary muscle group: <strong>{availableTertiaryGroups.find(mg => mg.id === tertiaryMuscleGroupId)?.name}</strong>
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
