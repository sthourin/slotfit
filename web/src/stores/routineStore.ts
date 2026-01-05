/**
 * Routine store using Zustand
 */
import { create } from 'zustand'
import { routineApi, RoutineTemplate as ApiRoutineTemplate } from '../services/api'

export interface RoutineSlot {
  id: string // Temporary ID for UI (or actual ID from backend)
  name: string | null  // Optional name for the slot
  order: number
  muscleGroupIds: number[]
  supersetTag: string | null
  selectedExerciseId: number | null  // Optional pre-selected exercise
  workoutStyle: string | null  // Optional workout style for this slot (overrides routine workout_style)
}

export interface RoutineTemplate {
  id?: number
  name: string
  routineType: 'anterior' | 'posterior' | 'full_body' | 'custom'
  workoutStyle: '5x5' | 'HIIT' | 'volume' | 'strength' | 'custom'
  description: string
  slots: RoutineSlot[]
}

interface RoutineStore {
  currentRoutine: RoutineTemplate | null
  saving: boolean
  loading: boolean
  setCurrentRoutine: (routine: RoutineTemplate | null) => void
  loadRoutine: (id: number) => Promise<void>
  saveRoutine: () => Promise<void>
  addSlot: (slot: Omit<RoutineSlot, 'id'>) => void
  updateSlot: (slotId: string, updates: Partial<RoutineSlot>) => void
  removeSlot: (slotId: string) => void
  reorderSlots: (slotIds: string[]) => void
  setSlotSupersetTag: (slotId: string, tag: string | null) => void
}

let slotIdCounter = 0

export const useRoutineStore = create<RoutineStore>((set, get) => ({
  currentRoutine: null,
  saving: false,
  loading: false,

  setCurrentRoutine: (routine) => set({ currentRoutine: routine }),

  loadRoutine: async (id: number) => {
    set({ loading: true })
    try {
      const apiRoutine = await routineApi.get(id)
      const routine: RoutineTemplate = {
        id: apiRoutine.id,
        name: apiRoutine.name,
        routineType: (apiRoutine.routine_type as any) || 'custom',
        workoutStyle: (apiRoutine.workout_style as any) || 'custom',
        description: apiRoutine.description || '',
        slots: apiRoutine.slots.map((slot) => ({
          id: `slot-${slot.id}`,
          name: slot.name || null,
          order: slot.order,
          muscleGroupIds: slot.muscle_group_ids,
          supersetTag: slot.superset_tag,
          selectedExerciseId: slot.selected_exercise_id || null,
          workoutStyle: slot.workout_style || null,
        })),
      }
      set({ currentRoutine: routine, loading: false })
    } catch (error) {
      console.error('Failed to load routine:', error)
      set({ loading: false })
      throw error
    }
  },

  saveRoutine: async () => {
    const { currentRoutine } = get()
    if (!currentRoutine) return

    set({ saving: true })
    try {
      const slots = currentRoutine.slots.map((slot) => ({
        name: slot.name || null,
        order: slot.order,
        muscle_group_ids: slot.muscleGroupIds || [],
        superset_tag: slot.supersetTag || null,
        selected_exercise_id: slot.selectedExerciseId || null,
        workout_style: slot.workoutStyle || null,
      }))

      if (currentRoutine.id) {
        // Update existing routine
        await routineApi.update(currentRoutine.id, {
          name: currentRoutine.name,
          routine_type: currentRoutine.routineType,
          workout_style: currentRoutine.workoutStyle,
          description: currentRoutine.description,
        })
        
        // Update slots (simplified - in production, handle individual slot updates)
        // For now, we'll delete all and recreate
        try {
          const existing = await routineApi.get(currentRoutine.id)
          for (const slot of existing.slots) {
            try {
              await routineApi.deleteSlot(currentRoutine.id, slot.id)
            } catch (deleteError) {
              console.warn(`Failed to delete slot ${slot.id}:`, deleteError)
              // Continue with other slots
            }
          }
          for (const slot of slots) {
            try {
              await routineApi.addSlot(currentRoutine.id, slot)
            } catch (addError) {
              console.error(`Failed to add slot:`, addError)
              throw addError
            }
          }
        } catch (slotError) {
          console.error('Error updating slots:', slotError)
          throw slotError
        }
        
        const final = await routineApi.get(currentRoutine.id)
        const routine: RoutineTemplate = {
          id: final.id,
          name: final.name,
          routineType: (final.routine_type as any) || 'custom',
          workoutStyle: (final.workout_style as any) || 'custom',
          description: final.description || '',
          slots: final.slots.map((s) => ({
            id: `slot-${s.id}`,
            name: s.name || null,
            order: s.order,
            muscleGroupIds: s.muscle_group_ids || [],
            supersetTag: s.superset_tag,
            selectedExerciseId: s.selected_exercise_id || null,
            workoutStyle: s.workout_style || null,
          })),
        }
        set({ currentRoutine: routine, saving: false })
      } else {
        // Create new routine
        const created = await routineApi.create({
          name: currentRoutine.name,
          routine_type: currentRoutine.routineType,
          workout_style: currentRoutine.workoutStyle,
          description: currentRoutine.description,
          slots: slots,
        })
        
        const routine: RoutineTemplate = {
          id: created.id,
          name: created.name,
          routineType: (created.routine_type as any) || 'custom',
          workoutStyle: (created.workout_style as any) || 'custom',
          description: created.description || '',
          slots: created.slots.map((s) => ({
            id: `slot-${s.id}`,
            name: s.name || null,
            order: s.order,
            muscleGroupIds: s.muscle_group_ids || [],
            supersetTag: s.superset_tag,
            selectedExerciseId: s.selected_exercise_id || null,
            workoutStyle: s.workout_style || null,
          })),
        }
        set({ currentRoutine: routine, saving: false })
      }
    } catch (error: any) {
      console.error('Failed to save routine:', error)
      let errorMessage = 'Unknown error'
      
      if (error?.code === 'ERR_NETWORK' || error?.message === 'Network Error') {
        errorMessage = 'Network Error: Cannot connect to server. Please ensure the backend is running at http://localhost:8000'
      } else if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error?.response?.data?.message) {
        errorMessage = error.response.data.message
      } else if (error?.message) {
        errorMessage = error.message
      }
      
      console.error('Error details:', errorMessage)
      set({ saving: false })
      throw new Error(errorMessage)
    }
  },

  addSlot: (slot) =>
    set((state) => {
      if (!state.currentRoutine) return state
      const newSlot: RoutineSlot = {
        ...slot,
        id: `slot-${++slotIdCounter}`,
        name: slot.name || null,
        selectedExerciseId: slot.selectedExerciseId || null,
        workoutStyle: slot.workoutStyle || null,
      }
      return {
        currentRoutine: {
          ...state.currentRoutine,
          slots: [...state.currentRoutine.slots, newSlot],
        },
      }
    }),

  updateSlot: (slotId, updates) =>
    set((state) => {
      if (!state.currentRoutine) return state
      return {
        currentRoutine: {
          ...state.currentRoutine,
          slots: state.currentRoutine.slots.map((slot) =>
            slot.id === slotId ? { ...slot, ...updates } : slot
          ),
        },
      }
    }),

  removeSlot: (slotId) =>
    set((state) => {
      if (!state.currentRoutine) return state
      return {
        currentRoutine: {
          ...state.currentRoutine,
          slots: state.currentRoutine.slots.filter((slot) => slot.id !== slotId),
        },
      }
    }),

  reorderSlots: (slotIds) =>
    set((state) => {
      if (!state.currentRoutine) return state
      const slotMap = new Map(state.currentRoutine.slots.map((s) => [s.id, s]))
      const reorderedSlots = slotIds
        .map((id) => slotMap.get(id))
        .filter((s): s is RoutineSlot => s !== undefined)
        .map((slot, index) => ({ ...slot, order: index + 1 }))
      return {
        currentRoutine: {
          ...state.currentRoutine,
          slots: reorderedSlots,
        },
      }
    }),

  setSlotSupersetTag: (slotId, tag) =>
    set((state) => {
      if (!state.currentRoutine) return state
      return {
        currentRoutine: {
          ...state.currentRoutine,
          slots: state.currentRoutine.slots.map((slot) =>
            slot.id === slotId ? { ...slot, supersetTag: tag } : slot
          ),
        },
      }
    }),
}))
