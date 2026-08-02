/**
 * Day plan store using Zustand
 */
import { create } from 'zustand'
import { listDayPlans, createDayPlan, updateDayPlan, deleteDayPlan } from '../services/dayPlans'
import type { DayPlan, DayPlanInput } from '../services/dayPlans'
import { listPatterns } from '../services/patterns'
import type { MovementPattern } from '../services/patterns'

interface DayPlanState {
  plans: DayPlan[]
  patterns: MovementPattern[]
  loading: boolean
  error: string | null
  fetchAll: () => Promise<void>
  save: (input: DayPlanInput, id?: number) => Promise<DayPlan>
  remove: (id: number) => Promise<void>
}

export const useDayPlanStore = create<DayPlanState>((set, get) => ({
  plans: [],
  patterns: [],
  loading: false,
  error: null,

  fetchAll: async () => {
    set({ loading: true, error: null })
    try {
      const [plans, patterns] = await Promise.all([listDayPlans(), listPatterns()])
      set({ plans, patterns, loading: false })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to load day plans', loading: false })
    }
  },

  save: async (input, id) => {
    const saved = id ? await updateDayPlan(id, input) : await createDayPlan(input)
    await get().fetchAll()
    return saved
  },

  remove: async (id) => {
    await deleteDayPlan(id)
    set({ plans: get().plans.filter((p) => p.id !== id) })
  },
}))
