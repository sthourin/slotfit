/**
 * Day plan API service
 */
import { apiClient } from './api'

export interface PatternGoal {
  id?: number
  pattern_id: number
  required: boolean
  target_sets: number | null
  rep_range_min: number | null
  rep_range_max: number | null
}

export interface DayPlan {
  id: number
  name: string
  description: string | null
  warmup_preferences: number[]
  rounds_target: number
  goals: PatternGoal[]
}

export type DayPlanInput = Omit<DayPlan, 'id'>

export async function listDayPlans(): Promise<DayPlan[]> {
  const { data } = await apiClient.get('/day-plans/')
  return data
}

export async function createDayPlan(input: DayPlanInput): Promise<DayPlan> {
  const { data } = await apiClient.post('/day-plans/', input)
  return data
}

export async function updateDayPlan(id: number, input: Partial<DayPlanInput>): Promise<DayPlan> {
  const { data } = await apiClient.put(`/day-plans/${id}`, input)
  return data
}

export async function deleteDayPlan(id: number): Promise<void> {
  await apiClient.delete(`/day-plans/${id}`)
}
