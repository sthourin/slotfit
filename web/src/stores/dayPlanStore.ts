/**
 * Day plan store using Zustand
 */
import { create } from 'zustand'
import { listDayPlans, createDayPlan, updateDayPlan, deleteDayPlan } from '../services/dayPlans'
import type { DayPlan, DayPlanInput } from '../services/dayPlans'
import { listPatterns } from '../services/patterns'
import type { MovementPattern } from '../services/patterns'
import { listStaples } from '../services/staples'

interface DayPlanState {
  plans: DayPlan[]
  patterns: MovementPattern[]
  /**
   * Active staples per pattern. A goal for a pattern with none can never be
   * satisfied, because every suggestion is drawn from the staple pool — the
   * form says so rather than letting the plan look complete.
   */
  stapleCountsByPattern: Record<number, number>
  loading: boolean
  error: string | null
  fetchAll: () => Promise<void>
  save: (input: DayPlanInput, id?: number) => Promise<DayPlan>
  remove: (id: number) => Promise<void>
}

export const useDayPlanStore = create<DayPlanState>((set, get) => ({
  plans: [],
  patterns: [],
  stapleCountsByPattern: {},
  loading: false,
  error: null,

  fetchAll: async () => {
    set({ loading: true, error: null })
    try {
      const [plans, patterns, staples] = await Promise.all([
        listDayPlans(),
        listPatterns(),
        listStaples(),
      ])
      const stapleCountsByPattern: Record<number, number> = {}
      for (const staple of staples) {
        if (staple.is_active) {
          stapleCountsByPattern[staple.pattern_id] =
            (stapleCountsByPattern[staple.pattern_id] ?? 0) + 1
        }
      }
      set({ plans, patterns, stapleCountsByPattern, loading: false })
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
