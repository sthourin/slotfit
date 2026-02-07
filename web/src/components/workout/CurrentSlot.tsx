/**
 * CurrentSlot Component - Slot-First Design
 * Displays the slot specification as the primary focus, with exercise as a selection that fills it
 */
import { useState, useEffect, useCallback } from 'react'
import type { ActiveWorkoutSlot } from '../../stores/workoutStore'
import type { Exercise } from '../../services/exercises'
import type { MuscleGroup } from '../../services/api'
import { useWorkoutStore } from '../../stores/workoutStore'
import { useUIStore } from '../../stores/uiStore'
import { muscleGroupApi } from '../../services/muscleGroups'
import { recommendationApi } from '../../services/recommendations'
import ExerciseSelector from './ExerciseSelector'
import { ConfirmDialog } from '../ui'
import { useConfirm } from '../../hooks/useConfirm'
import SlotSpecificationCard from './SlotSpecificationCard'
import ExerciseSelectionCard from './ExerciseSelectionCard'
import QuickAlternatives from './QuickAlternatives'

interface CurrentSlotProps {
  slot: ActiveWorkoutSlot
  slotIndex: number
  exercise: Exercise | null
  loadingExercise: boolean
}

interface Alternative {
  exerciseId: number
  exerciseName: string
  matchScore?: number
}

export default function CurrentSlot({
  slot,
  slotIndex,
  exercise,
  loadingExercise,
}: CurrentSlotProps) {
  const { startSlot, completeSlot, skipSlot, selectExerciseForSlot, activeWorkout } = useWorkoutStore()
  const { openModal, showToast } = useUIStore()
  const { confirm, dialogProps } = useConfirm()

  // Muscle group state
  const [muscleGroups, setMuscleGroups] = useState<MuscleGroup[]>([])
  const [muscleGroupsLoaded, setMuscleGroupsLoaded] = useState(false)

  // Recommendations state for quick alternatives
  const [alternatives, setAlternatives] = useState<Alternative[]>([])
  const [loadingAlternatives, setLoadingAlternatives] = useState(false)

  // Load muscle groups once
  useEffect(() => {
    if (!muscleGroupsLoaded) {
      muscleGroupApi.list().then((groups) => {
        setMuscleGroups(groups)
        setMuscleGroupsLoaded(true)
      }).catch((err) => {
        console.error('Failed to load muscle groups:', err)
      })
    }
  }, [muscleGroupsLoaded])

  // Load recommendations when slot changes
  const loadAlternatives = useCallback(async () => {
    const muscleIds = slot.primaryMuscleGroupId
      ? [slot.primaryMuscleGroupId, ...slot.secondaryMuscleGroupIds]
      : slot.muscleGroupIds

    if (muscleIds.length === 0) {
      setAlternatives([])
      return
    }

    setLoadingAlternatives(true)
    try {
      const response = await recommendationApi.getRecommendations({
        muscle_group_ids: muscleIds,
        available_equipment_ids: [], // TODO: Get from equipment profile
        workout_session_id: activeWorkout?.id,
        limit: 8,
      })

      setAlternatives(
        response.recommendations.map((rec) => ({
          exerciseId: rec.exercise_id,
          exerciseName: rec.exercise_name,
          matchScore: Math.round(rec.priority_score * 100),
        }))
      )
    } catch (err) {
      console.error('Failed to load recommendations:', err)
      setAlternatives([])
    } finally {
      setLoadingAlternatives(false)
    }
  }, [slot.primaryMuscleGroupId, slot.secondaryMuscleGroupIds, slot.muscleGroupIds, activeWorkout?.id])

  useEffect(() => {
    loadAlternatives()
  }, [loadAlternatives])

  // Resolve muscle group IDs to objects
  const primaryMuscleGroup = slot.primaryMuscleGroupId
    ? muscleGroups.find((mg) => mg.id === slot.primaryMuscleGroupId) || null
    : null

  const secondaryMuscleGroups = slot.secondaryMuscleGroupIds
    .map((id) => muscleGroups.find((mg) => mg.id === id))
    .filter((mg): mg is MuscleGroup => mg !== undefined)

  // Fallback: if no primary, treat first muscleGroupId as primary for display
  const displayPrimaryMuscleGroup = primaryMuscleGroup
    || (slot.muscleGroupIds.length > 0
      ? muscleGroups.find((mg) => mg.id === slot.muscleGroupIds[0]) || null
      : null)

  const displaySecondaryMuscleGroups = primaryMuscleGroup
    ? secondaryMuscleGroups
    : slot.muscleGroupIds.slice(1)
        .map((id) => muscleGroups.find((mg) => mg.id === id))
        .filter((mg): mg is MuscleGroup => mg !== undefined)

  // Handlers
  const handleSelectExercise = () => {
    openModal('exerciseSelector', { slotIndex, muscleGroupIds: slot.muscleGroupIds, slotId: slot.slotId })
  }

  const handleStart = () => {
    startSlot(slotIndex)
  }

  const handleComplete = () => {
    completeSlot(slotIndex)
    showToast('success', 'Slot completed!')
  }

  const handleSkip = async () => {
    const confirmed = await confirm({
      title: 'Skip Slot',
      message: 'Are you sure you want to skip this slot?',
      confirmLabel: 'Skip',
      variant: 'warning',
    })
    if (confirmed) {
      skipSlot(slotIndex)
      showToast('info', 'Slot skipped')
    }
  }

  const handleQuickSwap = async (exerciseId: number, exerciseName: string) => {
    await selectExerciseForSlot(slotIndex, exerciseId, exerciseName)
    showToast('success', `Switched to ${exerciseName}`)
    // Refresh alternatives
    loadAlternatives()
  }

  return (
    <>
      <ConfirmDialog {...dialogProps} />
      <div className="space-y-4">
        {/* Slot Specification Card - The primary visual element */}
        <SlotSpecificationCard
          slotNumber={slotIndex + 1}
          slotName={slot.slotName}
          slotType={slot.slotType}
          primaryMuscleGroup={displayPrimaryMuscleGroup}
          secondaryMuscleGroups={displaySecondaryMuscleGroups}
          workoutStyle={slot.workoutStyle}
          targetSets={slot.targetSets}
          targetRepsMin={slot.targetRepsMin}
          targetRepsMax={slot.targetRepsMax}
          targetWeight={slot.targetWeight}
          targetRestSeconds={slot.targetRestSeconds}
          completedSets={slot.sets.length}
          slotState={slot.slotState}
        />

        {/* Exercise Selection Card - Shows current exercise as one option */}
        <ExerciseSelectionCard
          exercise={exercise}
          loading={loadingExercise}
          primaryMuscleGroup={displayPrimaryMuscleGroup}
          secondaryMuscleGroups={displaySecondaryMuscleGroups}
          slotState={slot.slotState}
          onSwap={handleSelectExercise}
          onStart={handleStart}
          onComplete={handleComplete}
          onSelectExercise={handleSelectExercise}
        />

        {/* Quick Alternatives - Inline swap options */}
        {slot.slotState !== 'completed' && slot.slotState !== 'skipped' && (
          <QuickAlternatives
            currentExerciseId={slot.exerciseId}
            alternatives={alternatives}
            loading={loadingAlternatives}
            onSelect={handleQuickSwap}
            onShowMore={handleSelectExercise}
          />
        )}

        {/* Skip button - shown when slot is not completed */}
        {slot.slotState !== 'completed' && slot.slotState !== 'skipped' && (
          <div className="flex justify-end">
            <button
              onClick={handleSkip}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Skip Slot
            </button>
          </div>
        )}
      </div>

      {/* Exercise Selector Modal */}
      <ExerciseSelector
        slotIndex={slotIndex}
        muscleGroupIds={slot.muscleGroupIds}
        slotId={slot.slotId}
      />
    </>
  )
}
