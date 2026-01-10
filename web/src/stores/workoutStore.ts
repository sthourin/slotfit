/**
 * Workout Store - Active workout state management with localStorage persistence
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type {
  WorkoutSession,
  WorkoutSet,
  SlotState,
} from '../services/workouts'
import { workoutApi } from '../services/workouts'

export interface ActiveWorkoutSlot {
  slotId: number | null // From routine_slots.id
  exerciseId: number | null // Selected exercise
  exerciseName: string | null
  muscleGroupIds: number[] // Muscle group IDs for this slot (from routine slot)
  slotState: SlotState
  sets: WorkoutSet[]
  startedAt: string | null // ISO date string
  stoppedAt: string | null // ISO date string
}

interface WorkoutStore {
  // Active workout session
  activeWorkout: WorkoutSession | null
  activeSlots: ActiveWorkoutSlot[]
  currentSlotIndex: number | null
  
  // Loading states
  loading: boolean
  saving: boolean
  
  // Actions
  initializeWorkout: (routineId: number, equipmentProfileId?: number) => Promise<void>
  initializeWorkoutWithSlots: (routineId: number, slots: Array<{ slotId: number; exerciseId: number | null; exerciseName: string | null }>, equipmentProfileId?: number) => Promise<void>
  loadWorkout: (workoutId: number) => Promise<void>
  startWorkout: () => Promise<void>
  pauseWorkout: () => Promise<void>
  resumeWorkout: () => Promise<void>
  completeWorkout: () => Promise<void>
  abandonWorkout: () => Promise<void>
  
  // Slot management
  selectExerciseForSlot: (slotIndex: number, exerciseId: number, exerciseName: string) => void
  startSlot: (slotIndex: number) => void
  completeSlot: (slotIndex: number) => void
  skipSlot: (slotIndex: number) => void
  setCurrentSlot: (slotIndex: number | null) => void
  nextSlot: () => void
  previousSlot: () => void
  
  // Set management
      addSet: (slotIndex: number, setData: Omit<WorkoutSet, 'id' | 'workout_exercise_id'>) => void
  updateSet: (slotIndex: number, setIndex: number, updates: Partial<WorkoutSet>) => void
  removeSet: (slotIndex: number, setIndex: number) => void
  
  // Clear active workout (for cleanup)
  clearActiveWorkout: () => void
}

const STORAGE_KEY = 'slotfit-active-workout'

export const useWorkoutStore = create<WorkoutStore>()(
  persist(
    (set, get) => ({
      activeWorkout: null,
      activeSlots: [],
      currentSlotIndex: null,
      loading: false,
      saving: false,

      initializeWorkout: async (routineId: number, equipmentProfileId?: number) => {
        set({ loading: true })
        try {
          // Create a new workout session
          const workout = await workoutApi.create({
            routine_template_id: routineId,
            state: 'draft',
          })
          
          // Load routine to get slots
          const { routineApi } = await import('../services/routines')
          const routine = await routineApi.get(routineId)
          
          // Initialize slots from routine
          const activeSlots: ActiveWorkoutSlot[] = routine.slots.map((slot) => ({
            slotId: slot.id,
            exerciseId: slot.selected_exercise_id || null,
            exerciseName: null, // Will be filled when exercise is selected
            muscleGroupIds: slot.muscle_group_ids,
            slotState: 'not_started',
            sets: [],
            startedAt: null,
            stoppedAt: null,
          }))
          
          set({
            activeWorkout: workout,
            activeSlots,
            currentSlotIndex: activeSlots.length > 0 ? 0 : null,
            loading: false,
          })
        } catch (error) {
          console.error('Failed to initialize workout:', error)
          set({ loading: false })
          throw error
        }
      },

      initializeWorkoutWithSlots: async (
        routineId: number,
        slots: Array<{ slotId: number; exerciseId: number | null; exerciseName: string | null }>,
        equipmentProfileId?: number
      ) => {
        set({ loading: true })
        try {
          // Create a new workout session
          const workout = await workoutApi.create({
            routine_template_id: routineId,
            state: 'draft',
          })
          
          // Load routine to get muscle_group_ids for slots
          const { routineApi } = await import('../services/routines')
          const routine = await routineApi.get(routineId)
          
          // Create a map of slotId to muscle_group_ids
          const slotMuscleGroupsMap = new Map<number, number[]>()
          routine.slots.forEach((slot) => {
            slotMuscleGroupsMap.set(slot.id, slot.muscle_group_ids)
          })
          
          // Initialize slots with pre-filled exercises
          const activeSlots: ActiveWorkoutSlot[] = slots.map((slot) => ({
            slotId: slot.slotId,
            exerciseId: slot.exerciseId,
            exerciseName: slot.exerciseName,
            muscleGroupIds: slotMuscleGroupsMap.get(slot.slotId) || [],
            slotState: 'not_started',
            sets: [],
            startedAt: null,
            stoppedAt: null,
          }))
          
          set({
            activeWorkout: workout,
            activeSlots,
            currentSlotIndex: activeSlots.length > 0 ? 0 : null,
            loading: false,
          })
        } catch (error) {
          console.error('Failed to initialize workout with slots:', error)
          set({ loading: false })
          throw error
        }
      },

      loadWorkout: async (workoutId: number) => {
        set({ loading: true })
        try {
          const workout = await workoutApi.get(workoutId)
          
          // Load routine to get muscle_group_ids for slots
          const slotMuscleGroupsMap = new Map<number, number[]>()
          if (workout.routine_template_id) {
            try {
              const { routineApi } = await import('../services/routines')
              const routine = await routineApi.get(workout.routine_template_id)
              routine.slots.forEach((slot) => {
                slotMuscleGroupsMap.set(slot.id, slot.muscle_group_ids)
              })
            } catch (error) {
              console.error('Failed to load routine for muscle groups:', error)
            }
          }
          
          // Convert workout exercises to active slots
          const activeSlots: ActiveWorkoutSlot[] = workout.exercises.map((exercise) => ({
            slotId: exercise.slot_id,
            exerciseId: exercise.exercise_id,
            exerciseName: null, // Would need to fetch exercise name separately
            muscleGroupIds: slotMuscleGroupsMap.get(exercise.slot_id || 0) || [],
            slotState: exercise.slot_state,
            sets: exercise.sets,
            startedAt: exercise.started_at,
            stoppedAt: exercise.stopped_at,
          }))
          
          // Find current slot (first in_progress or first not_started)
          const currentIndex =
            activeSlots.findIndex((slot) => slot.slotState === 'in_progress') ??
            activeSlots.findIndex((slot) => slot.slotState === 'not_started') ??
            null

          set({
            activeWorkout: workout,
            activeSlots,
            currentSlotIndex: currentIndex >= 0 ? currentIndex : null,
            loading: false,
          })
        } catch (error) {
          console.error('Failed to load workout:', error)
          set({ loading: false })
          throw error
        }
      },

      startWorkout: async () => {
        const { activeWorkout } = get()
        if (!activeWorkout) return

        set({ saving: true })
        try {
          const updated = await workoutApi.start(activeWorkout.id)
          set({
            activeWorkout: updated,
            saving: false,
          })
        } catch (error) {
          console.error('Failed to start workout:', error)
          set({ saving: false })
          throw error
        }
      },

      pauseWorkout: async () => {
        const { activeWorkout } = get()
        if (!activeWorkout) return

        set({ saving: true })
        try {
          const updated = await workoutApi.pause(activeWorkout.id)
          set({
            activeWorkout: updated,
            saving: false,
          })
        } catch (error) {
          console.error('Failed to pause workout:', error)
          set({ saving: false })
          throw error
        }
      },

      resumeWorkout: async () => {
        const { activeWorkout } = get()
        if (!activeWorkout) return

        set({ saving: true })
        try {
          // Resume is essentially starting again after pause
          const updated = await workoutApi.start(activeWorkout.id)
          set({
            activeWorkout: updated,
            saving: false,
          })
        } catch (error) {
          console.error('Failed to resume workout:', error)
          set({ saving: false })
          throw error
        }
      },

      completeWorkout: async () => {
        const { activeWorkout } = get()
        if (!activeWorkout) return

        set({ saving: true })
        try {
          const updated = await workoutApi.complete(activeWorkout.id)
          set({
            activeWorkout: updated,
            saving: false,
          })
          // Clear from localStorage after completion
          setTimeout(() => {
            get().clearActiveWorkout()
          }, 1000)
        } catch (error) {
          console.error('Failed to complete workout:', error)
          set({ saving: false })
          throw error
        }
      },

      abandonWorkout: async () => {
        const { activeWorkout } = get()
        if (!activeWorkout) return

        set({ saving: true })
        try {
          const updated = await workoutApi.abandon(activeWorkout.id)
          set({
            activeWorkout: updated,
            saving: false,
          })
          // Clear from localStorage after abandonment
          setTimeout(() => {
            get().clearActiveWorkout()
          }, 1000)
        } catch (error) {
          console.error('Failed to abandon workout:', error)
          set({ saving: false })
          throw error
        }
      },

      selectExerciseForSlot: (slotIndex: number, exerciseId: number, exerciseName: string) => {
        set((state) => {
          const newSlots = [...state.activeSlots]
          if (!newSlots[slotIndex]) {
            // Create new slot if it doesn't exist
            newSlots[slotIndex] = {
              slotId: null,
              exerciseId,
              exerciseName,
              muscleGroupIds: [], // Default empty, should be populated from routine slot
              slotState: 'not_started',
              sets: [],
              startedAt: null,
              stoppedAt: null,
            }
          } else {
            newSlots[slotIndex] = {
              ...newSlots[slotIndex],
              exerciseId,
              exerciseName,
            }
          }
          return { activeSlots: newSlots }
        })
      },

      startSlot: (slotIndex: number) => {
        set((state) => {
          const newSlots = [...state.activeSlots]
          if (newSlots[slotIndex]) {
            newSlots[slotIndex] = {
              ...newSlots[slotIndex],
              slotState: 'in_progress',
              startedAt: new Date().toISOString(),
            }
          }
          return {
            activeSlots: newSlots,
            currentSlotIndex: slotIndex,
          }
        })
      },

      completeSlot: (slotIndex: number) => {
        set((state) => {
          const newSlots = [...state.activeSlots]
          if (newSlots[slotIndex]) {
            newSlots[slotIndex] = {
              ...newSlots[slotIndex],
              slotState: 'completed',
              stoppedAt: new Date().toISOString(),
            }
          }
          // Move to next slot
          const nextIndex = slotIndex + 1 < newSlots.length ? slotIndex + 1 : null
          return {
            activeSlots: newSlots,
            currentSlotIndex: nextIndex,
          }
        })
      },

      skipSlot: (slotIndex: number) => {
        set((state) => {
          const newSlots = [...state.activeSlots]
          if (newSlots[slotIndex]) {
            newSlots[slotIndex] = {
              ...newSlots[slotIndex],
              slotState: 'skipped',
            }
          }
          // Move to next slot
          const nextIndex = slotIndex + 1 < newSlots.length ? slotIndex + 1 : null
          return {
            activeSlots: newSlots,
            currentSlotIndex: nextIndex,
          }
        })
      },

      setCurrentSlot: (slotIndex: number | null) => {
        set({ currentSlotIndex: slotIndex })
      },

      nextSlot: () => {
        const { currentSlotIndex, activeSlots } = get()
        if (currentSlotIndex === null) {
          // Start with first slot
          if (activeSlots.length > 0) {
            set({ currentSlotIndex: 0 })
          }
        } else if (currentSlotIndex + 1 < activeSlots.length) {
          set({ currentSlotIndex: currentSlotIndex + 1 })
        }
      },

      previousSlot: () => {
        const { currentSlotIndex } = get()
        if (currentSlotIndex !== null && currentSlotIndex > 0) {
          set({ currentSlotIndex: currentSlotIndex - 1 })
        }
      },

      addSet: (slotIndex: number, setData: Omit<WorkoutSet, 'id' | 'workout_exercise_id'>) => {
        set((state) => {
          const newSlots = [...state.activeSlots]
          if (newSlots[slotIndex]) {
            const setNumber = newSlots[slotIndex].sets.length + 1
            const newSet: WorkoutSet = {
              ...setData,
              id: Date.now(), // Temporary ID until saved to backend
              workout_exercise_id: 0, // Will be set when saved
              set_number: setData.set_number || setNumber,
            }
            newSlots[slotIndex] = {
              ...newSlots[slotIndex],
              sets: [...newSlots[slotIndex].sets, newSet],
            }
          }
          return { activeSlots: newSlots }
        })
      },

      updateSet: (slotIndex: number, setIndex: number, updates: Partial<WorkoutSet>) => {
        set((state) => {
          const newSlots = [...state.activeSlots]
          if (newSlots[slotIndex] && newSlots[slotIndex].sets[setIndex]) {
            const newSets = [...newSlots[slotIndex].sets]
            newSets[setIndex] = { ...newSets[setIndex], ...updates }
            newSlots[slotIndex] = {
              ...newSlots[slotIndex],
              sets: newSets,
            }
          }
          return { activeSlots: newSlots }
        })
      },

      removeSet: (slotIndex: number, setIndex: number) => {
        set((state) => {
          const newSlots = [...state.activeSlots]
          if (newSlots[slotIndex]) {
            const newSets = newSlots[slotIndex].sets.filter((_, idx) => idx !== setIndex)
            newSlots[slotIndex] = {
              ...newSlots[slotIndex],
              sets: newSets,
            }
          }
          return { activeSlots: newSlots }
        })
      },

      clearActiveWorkout: () => {
        set({
          activeWorkout: null,
          activeSlots: [],
          currentSlotIndex: null,
        })
      },
    }),
    {
      name: STORAGE_KEY,
      // Only persist active workout if it's in draft or active state
      partialize: (state) => {
        if (
          state.activeWorkout &&
          (state.activeWorkout.state === 'draft' || state.activeWorkout.state === 'active')
        ) {
          return {
            activeWorkout: state.activeWorkout,
            activeSlots: state.activeSlots,
            currentSlotIndex: state.currentSlotIndex,
          }
        }
        return {}
      },
    }
  )
)
