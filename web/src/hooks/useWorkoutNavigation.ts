/**
 * Workout Navigation Hook
 * Provides navigation functions and state for workout interface
 */
import { useCallback, useRef } from 'react'
import { useWorkoutStore, type ActiveWorkoutSlot } from '../stores/workoutStore'

interface UseWorkoutNavigationOptions {
  activeSlots: ActiveWorkoutSlot[]
  currentSlotIndex: number | null
  onRestTimerToggle?: (isRunning: boolean) => void
}

export interface WorkoutNavigation {
  // Navigation
  goToPreviousSlot: () => void
  goToNextSlot: () => void
  goToSlot: (index: number) => void
  
  // Slot actions
  skipCurrentSlot: () => void
  startCurrentSlot: () => void
  completeCurrentSlot: () => void
  
  // Set actions
  addSetToCurrentSlot: () => void
  
  // Rest timer
  toggleRestTimer: () => void
  
  // Utilities
  canGoPrevious: boolean
  canGoNext: boolean
  isFirstSlot: boolean
  isLastSlot: boolean
}

/**
 * Hook that provides workout navigation functions
 */
export function useWorkoutNavigation({
  activeSlots,
  currentSlotIndex,
  onRestTimerToggle,
}: UseWorkoutNavigationOptions): WorkoutNavigation {
  const {
    nextSlot,
    previousSlot,
    setCurrentSlot,
    skipSlot,
    startSlot,
    completeSlot,
    addSet,
  } = useWorkoutStore()

  const goToPreviousSlot = useCallback(() => {
    if (currentSlotIndex !== null && currentSlotIndex > 0) {
      previousSlot()
    }
  }, [currentSlotIndex, previousSlot])

  const goToNextSlot = useCallback(() => {
    if (currentSlotIndex !== null && currentSlotIndex < activeSlots.length - 1) {
      nextSlot()
    }
  }, [currentSlotIndex, activeSlots.length, nextSlot])

  const goToSlot = useCallback(
    (index: number) => {
      if (index >= 0 && index < activeSlots.length) {
        setCurrentSlot(index)
      }
    },
    [activeSlots.length, setCurrentSlot]
  )

  const skipCurrentSlot = useCallback(() => {
    if (currentSlotIndex !== null) {
      if (window.confirm('Are you sure you want to skip this slot?')) {
        skipSlot(currentSlotIndex)
      }
    }
  }, [currentSlotIndex, skipSlot])

  const startCurrentSlot = useCallback(() => {
    if (currentSlotIndex !== null) {
      startSlot(currentSlotIndex)
    }
  }, [currentSlotIndex, startSlot])

  const completeCurrentSlot = useCallback(() => {
    if (currentSlotIndex !== null) {
      completeSlot(currentSlotIndex)
    }
  }, [currentSlotIndex, completeSlot])

  const addSetToCurrentSlot = useCallback(() => {
    if (currentSlotIndex !== null) {
      const slot = activeSlots[currentSlotIndex]
      if (slot && slot.slotState === 'in_progress') {
        // Try to use the SetTracker's addSet function if available
        const addSetFn = (window as Record<string, unknown>).__setTrackerAddSet
        if (addSetFn && typeof addSetFn === 'function') {
          addSetFn()
        } else {
          // Fallback: add set with null values
          const setNumber = slot.sets.length + 1
          addSet(currentSlotIndex, {
            set_number: setNumber,
            reps: null,
            weight: null,
            rest_seconds: null,
            notes: null,
          })
        }
      }
    }
  }, [currentSlotIndex, activeSlots, addSet])

  // Rest timer state management (external control)
  const restTimerStateRef = useRef<{ isRunning: boolean }>({ isRunning: false })

  const toggleRestTimer = useCallback(() => {
    restTimerStateRef.current.isRunning = !restTimerStateRef.current.isRunning
    onRestTimerToggle?.(restTimerStateRef.current.isRunning)
  }, [onRestTimerToggle])

  const canGoPrevious = currentSlotIndex !== null && currentSlotIndex > 0
  const canGoNext =
    currentSlotIndex !== null && currentSlotIndex < activeSlots.length - 1
  const isFirstSlot = currentSlotIndex === 0
  const isLastSlot =
    currentSlotIndex !== null && currentSlotIndex === activeSlots.length - 1

  return {
    goToPreviousSlot,
    goToNextSlot,
    goToSlot,
    skipCurrentSlot,
    startCurrentSlot,
    completeCurrentSlot,
    addSetToCurrentSlot,
    toggleRestTimer,
    canGoPrevious,
    canGoNext,
    isFirstSlot,
    isLastSlot,
  }
}
