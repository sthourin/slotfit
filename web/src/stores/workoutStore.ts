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
  workoutExerciseId: number | null // Backend workout_exercise.id (for syncing sets)
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
  selectExerciseForSlot: (slotIndex: number, exerciseId: number, exerciseName: string) => Promise<void>
  startSlot: (slotIndex: number) => Promise<void>
  completeSlot: (slotIndex: number) => Promise<void>
  skipSlot: (slotIndex: number) => void
  setCurrentSlot: (slotIndex: number | null) => void
  nextSlot: () => void
  previousSlot: () => void
  
  // Set management
  addSet: (slotIndex: number, setData: Omit<WorkoutSet, 'id' | 'workout_exercise_id'>) => Promise<void>
  updateSet: (slotIndex: number, setIndex: number, updates: Partial<WorkoutSet>) => Promise<void>
  removeSet: (slotIndex: number, setIndex: number) => Promise<void>
  reorderSets: (slotIndex: number, orderedSetIds: number[]) => Promise<void>
  syncSlotSets: (slotIndex: number) => Promise<void>
  
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
            workoutExerciseId: null, // Will be set when exercise is added to workout
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
            workoutExerciseId: null, // Will be set when exercise is added to workout
            muscleGroupIds: slotMuscleGroupsMap.get(slot.slotId) || [],
            slotState: 'not_started',
            sets: [],
            startedAt: null,
            stoppedAt: null,
          }))
          
          // Add exercises to workout if they're pre-filled
          for (let i = 0; i < slots.length; i++) {
            const slot = slots[i]
            if (slot.exerciseId && slot.slotId) {
              try {
                const workoutExercise = await workoutApi.addExercise(workout.id, {
                  routine_slot_id: slot.slotId,
                  exercise_id: slot.exerciseId,
                })
                // Update slot with workout exercise ID
                activeSlots[i].workoutExerciseId = workoutExercise.id
              } catch (error) {
                console.error(`Failed to add exercise ${slot.exerciseId} to workout:`, error)
              }
            }
          }
          
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
            workoutExerciseId: exercise.id, // Backend workout_exercise.id
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
        const { activeWorkout, activeSlots } = get()
        if (!activeWorkout) return

        set({ saving: true })
        try {
          // Sync all sets and exercise states before completing
          for (let i = 0; i < activeSlots.length; i++) {
            const slot = activeSlots[i]
            if (slot?.workoutExerciseId) {
              // Sync exercise state
              if (slot.slotState !== 'not_started') {
                await workoutApi.updateExercise(activeWorkout.id, slot.workoutExerciseId, {
                  slot_state: slot.slotState,
                  started_at: slot.startedAt,
                  stopped_at: slot.stoppedAt,
                })
              }
              // Sync all sets
              await get().syncSlotSets(i)
            }
          }
          
          // Now complete the workout
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

      selectExerciseForSlot: async (slotIndex: number, exerciseId: number, exerciseName: string) => {
        const { activeWorkout, activeSlots } = get()
        if (!activeWorkout) return

        // Update local state immediately
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

        // Sync to backend if we have a slotId and workout is started
        const slot = activeSlots[slotIndex]
        if (slot?.slotId && (activeWorkout.state === 'active' || activeWorkout.state === 'draft')) {
          try {
            const workoutExercise = await workoutApi.addExercise(activeWorkout.id, {
              routine_slot_id: slot.slotId,
              exercise_id: exerciseId,
            })
            // Update slot with workout exercise ID
            set((state) => {
              const newSlots = [...state.activeSlots]
              if (newSlots[slotIndex]) {
                newSlots[slotIndex] = {
                  ...newSlots[slotIndex],
                  workoutExerciseId: workoutExercise.id,
                }
              }
              return { activeSlots: newSlots }
            })
          } catch (error) {
            console.error('Failed to sync exercise to backend:', error)
            // Don't throw - local state is already updated
          }
        }
      },

      startSlot: async (slotIndex: number) => {
        const { activeWorkout, activeSlots } = get()
        const slot = activeSlots[slotIndex]
        
        // Update local state
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
        
        // Sync to backend if workout exercise exists
        if (activeWorkout && slot?.workoutExerciseId) {
          try {
            await workoutApi.updateExercise(activeWorkout.id, slot.workoutExerciseId, {
              slot_state: 'in_progress',
              started_at: new Date().toISOString(),
            })
          } catch (error) {
            console.error('Failed to sync slot start to backend:', error)
          }
        }
      },

      completeSlot: async (slotIndex: number) => {
        const { activeWorkout, activeSlots } = get()
        const slot = activeSlots[slotIndex]
        
        // Update local state
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
        
        // Sync to backend if workout exercise exists
        if (activeWorkout && slot?.workoutExerciseId) {
          try {
            await workoutApi.updateExercise(activeWorkout.id, slot.workoutExerciseId, {
              slot_state: 'completed',
              stopped_at: new Date().toISOString(),
            })
            // Sync all sets for this slot
            await get().syncSlotSets(slotIndex)
          } catch (error) {
            console.error('Failed to sync slot completion to backend:', error)
          }
        }
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

      addSet: async (slotIndex: number, setData: Omit<WorkoutSet, 'id' | 'workout_exercise_id'>) => {
        const { activeWorkout, activeSlots } = get()
        const slot = activeSlots[slotIndex]
        
        // Update local state immediately
        set((state) => {
          const newSlots = [...state.activeSlots]
          if (newSlots[slotIndex]) {
            const setNumber = newSlots[slotIndex].sets.length + 1
            const newSet: WorkoutSet = {
              ...setData,
              id: Date.now(), // Temporary ID until saved to backend
              workout_exercise_id: slot?.workoutExerciseId || 0,
              set_number: setData.set_number || setNumber,
            }
            newSlots[slotIndex] = {
              ...newSlots[slotIndex],
              sets: [...newSlots[slotIndex].sets, newSet],
            }
          }
          return { activeSlots: newSlots }
        })
        
        // Sync to backend if workout exercise exists
        if (activeWorkout && slot?.workoutExerciseId) {
          try {
            const savedSet = await workoutApi.createSet(activeWorkout.id, slot.workoutExerciseId, {
              set_number: setData.set_number || slot.sets.length + 1,
              reps: setData.reps,
              weight: setData.weight,
              rest_seconds: setData.rest_seconds,
              rpe: setData.rpe,
              notes: setData.notes,
            })
            // Update local set with backend ID
            set((state) => {
              const newSlots = [...state.activeSlots]
              if (newSlots[slotIndex]) {
                const newSets = [...newSlots[slotIndex].sets]
                const lastIndex = newSets.length - 1
                if (lastIndex >= 0) {
                  newSets[lastIndex] = savedSet
                }
                newSlots[slotIndex] = {
                  ...newSlots[slotIndex],
                  sets: newSets,
                }
              }
              return { activeSlots: newSlots }
            })
          } catch (error) {
            console.error('Failed to sync set to backend:', error)
            // Don't throw - local state is already updated
          }
        }
      },

      updateSet: async (slotIndex: number, setIndex: number, updates: Partial<WorkoutSet>) => {
        const { activeWorkout, activeSlots } = get()
        const slot = activeSlots[slotIndex]
        const setToUpdate = slot?.sets[setIndex]
        const shouldRenumber = typeof updates.set_number === 'number'
        const updatedSets = slot
          ? slot.sets.map((workoutSet, idx) =>
              idx === setIndex ? { ...workoutSet, ...updates } : workoutSet
            )
          : []
        const nextSets = shouldRenumber
          ? [...updatedSets]
              .sort((a, b) => a.set_number - b.set_number)
              .map((workoutSet, idx) => ({
                ...workoutSet,
                set_number: idx + 1,
              }))
          : updatedSets
        const updatedSetForSync =
          setToUpdate ? nextSets.find((workoutSet) => workoutSet.id === setToUpdate.id) : undefined
        
        // Update local state immediately
        set((state) => {
          const newSlots = [...state.activeSlots]
          if (newSlots[slotIndex] && newSlots[slotIndex].sets[setIndex]) {
            newSlots[slotIndex] = {
              ...newSlots[slotIndex],
              sets: nextSets,
            }
          }
          return { activeSlots: newSlots }
        })
        
        // Sync to backend if set has backend ID (real IDs are typically < 1000000, temporary IDs from Date.now() are > 1000000)
        if (activeWorkout && slot?.workoutExerciseId && setToUpdate?.id) {
          // Check if it's a real backend ID (typically small integers) vs temporary (Date.now() which is large)
          const isRealId = setToUpdate.id < 1000000
          if (isRealId) {
            try {
              await workoutApi.updateSet(activeWorkout.id, slot.workoutExerciseId, setToUpdate.id, {
                set_number: shouldRenumber ? updatedSetForSync?.set_number : undefined,
                reps: updates.reps,
                weight: updates.weight,
                rest_seconds: updates.rest_seconds,
                rpe: updates.rpe,
                notes: updates.notes,
              })
            } catch (error) {
              console.error('Failed to sync set update to backend:', error)
              // Don't throw - local state is already updated
            }
          } else {
            // Temporary ID - create new set in backend
            try {
              const finalSetNumber = updatedSetForSync?.set_number ?? setToUpdate.set_number
              const savedSet = await workoutApi.createSet(activeWorkout.id, slot.workoutExerciseId, {
                set_number: finalSetNumber,
                reps: updates.reps ?? setToUpdate.reps,
                weight: updates.weight ?? setToUpdate.weight,
                rest_seconds: updates.rest_seconds ?? setToUpdate.rest_seconds,
                rpe: updates.rpe ?? setToUpdate.rpe,
                notes: updates.notes ?? setToUpdate.notes,
              })
              // Update local set with backend ID
              set((state) => {
                const newSlots = [...state.activeSlots]
                if (newSlots[slotIndex] && newSlots[slotIndex].sets[setIndex]) {
                  const newSets = [...newSlots[slotIndex].sets]
                  newSets[setIndex] = savedSet
                  newSlots[slotIndex] = {
                    ...newSlots[slotIndex],
                    sets: newSets,
                  }
                }
                return { activeSlots: newSlots }
              })
            } catch (error) {
              console.error('Failed to sync set creation to backend:', error)
            }
          }
        }

        // Sync renumbered sets to backend when manual ordering changes
        if (shouldRenumber && activeWorkout && slot?.workoutExerciseId) {
          for (const workoutSet of nextSets) {
            if (workoutSet.id < 1000000) {
              try {
                await workoutApi.updateSet(
                  activeWorkout.id,
                  slot.workoutExerciseId,
                  workoutSet.id,
                  { set_number: workoutSet.set_number }
                )
              } catch (error) {
                console.error('Failed to sync set renumber to backend:', error)
              }
            }
          }
        }
      },

      removeSet: async (slotIndex: number, setIndex: number) => {
        const { activeWorkout, activeSlots } = get()
        const slot = activeSlots[slotIndex]
        const setToRemove = slot?.sets[setIndex]
        
        // Update local state immediately
        const renumberedSets = slot
          ? slot.sets
              .filter((_, idx) => idx !== setIndex)
              .map((workoutSet, idx) => ({
                ...workoutSet,
                set_number: idx + 1,
              }))
          : []

        set((state) => {
          const newSlots = [...state.activeSlots]
          if (newSlots[slotIndex]) {
            newSlots[slotIndex] = {
              ...newSlots[slotIndex],
              sets: renumberedSets,
            }
          }
          return { activeSlots: newSlots }
        })
        
        // Sync to backend if set has backend ID (real IDs are typically < 1000000)
        if (activeWorkout && slot?.workoutExerciseId && setToRemove?.id && setToRemove.id < 1000000) {
          try {
            await workoutApi.deleteSet(activeWorkout.id, slot.workoutExerciseId, setToRemove.id)
          } catch (error) {
            console.error('Failed to sync set deletion to backend:', error)
            // Don't throw - local state is already updated
          }
        }

        // Sync renumbered sets to backend (real IDs only)
        if (activeWorkout && slot?.workoutExerciseId) {
          for (const workoutSet of renumberedSets) {
            if (workoutSet.id < 1000000 && workoutSet.set_number) {
              try {
                await workoutApi.updateSet(
                  activeWorkout.id,
                  slot.workoutExerciseId,
                  workoutSet.id,
                  { set_number: workoutSet.set_number }
                )
              } catch (error) {
                console.error('Failed to sync set renumber to backend:', error)
              }
            }
          }
        }
      },

      reorderSets: async (slotIndex: number, orderedSetIds: number[]) => {
        const { activeWorkout, activeSlots } = get()
        const slot = activeSlots[slotIndex]
        if (!slot || orderedSetIds.length <= 1) return

        const setMap = new Map(slot.sets.map((workoutSet) => [workoutSet.id, workoutSet]))
        const orderedIdSet = new Set(orderedSetIds)
        const orderedSets = orderedSetIds
          .map((setId) => setMap.get(setId))
          .filter((workoutSet): workoutSet is WorkoutSet => Boolean(workoutSet))
        const missingSets = slot.sets.filter((workoutSet) => !orderedIdSet.has(workoutSet.id))
        const renumberedSets = [...orderedSets, ...missingSets].map((workoutSet, idx) => ({
          ...workoutSet,
          set_number: idx + 1,
        }))

        set((state) => {
          const newSlots = [...state.activeSlots]
          if (newSlots[slotIndex]) {
            newSlots[slotIndex] = {
              ...newSlots[slotIndex],
              sets: renumberedSets,
            }
          }
          return { activeSlots: newSlots }
        })

        if (activeWorkout && slot.workoutExerciseId) {
          for (const workoutSet of renumberedSets) {
            if (workoutSet.id < 1000000) {
              try {
                await workoutApi.updateSet(
                  activeWorkout.id,
                  slot.workoutExerciseId,
                  workoutSet.id,
                  { set_number: workoutSet.set_number }
                )
              } catch (error) {
                console.error('Failed to sync set reorder to backend:', error)
              }
            }
          }
        }
      },
      
      // Sync all sets for a slot to backend
      syncSlotSets: async (slotIndex: number) => {
        const { activeWorkout, activeSlots } = get()
        const slot = activeSlots[slotIndex]
        
        if (!activeWorkout || !slot?.workoutExerciseId) return
        
        try {
          // Get all sets that need syncing (temporary IDs from Date.now() are > 1000000)
          const setsToSync = slot.sets.filter((s) => !s.id || s.id >= 1000000)
          
          for (const setToSync of setsToSync) {
            try {
              const savedSet = await workoutApi.createSet(activeWorkout.id, slot.workoutExerciseId, {
                set_number: setToSync.set_number,
                reps: setToSync.reps,
                weight: setToSync.weight,
                rest_seconds: setToSync.rest_seconds,
                rpe: setToSync.rpe,
                notes: setToSync.notes,
              })
              
              // Update local set with backend ID
              set((state) => {
                const newSlots = [...state.activeSlots]
                if (newSlots[slotIndex]) {
                  const setIndex = newSlots[slotIndex].sets.findIndex((s) => s.id === setToSync.id)
                  if (setIndex >= 0) {
                    const newSets = [...newSlots[slotIndex].sets]
                    newSets[setIndex] = savedSet
                    newSlots[slotIndex] = {
                      ...newSlots[slotIndex],
                      sets: newSets,
                    }
                  }
                }
                return { activeSlots: newSlots }
              })
            } catch (error) {
              console.error(`Failed to sync set ${setToSync.set_number} to backend:`, error)
            }
          }
        } catch (error) {
          console.error('Failed to sync slot sets to backend:', error)
        }
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
