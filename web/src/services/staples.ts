/**
 * Staples and exercise preferences API service
 */
import { apiClient } from './api'

export interface Staple {
  id: number
  pattern_id: number
  exercise_id: number
  exercise_name: string
  is_active: boolean
  added_at: string
  last_performed: string | null
}

export interface ExercisePreference {
  id: number
  exercise_id: number
  exercise_name: string
  preference: string
}

export async function listStaples(): Promise<Staple[]> {
  const { data } = await apiClient.get('/staples/')
  return data
}

export async function createStaple(exerciseId: number): Promise<Staple> {
  const { data } = await apiClient.post('/staples/', { exercise_id: exerciseId })
  return data
}

export async function patchStaple(id: number, isActive: boolean): Promise<Staple> {
  const { data } = await apiClient.patch(`/staples/${id}`, { is_active: isActive })
  return data
}

export async function deleteStaple(id: number): Promise<void> {
  await apiClient.delete(`/staples/${id}`)
}

export async function listPreferences(): Promise<ExercisePreference[]> {
  const { data } = await apiClient.get('/staples/preferences')
  return data
}

export async function createPreference(exerciseId: number): Promise<ExercisePreference> {
  const { data } = await apiClient.post('/staples/preferences', { exercise_id: exerciseId })
  return data
}

export async function deletePreference(id: number): Promise<void> {
  await apiClient.delete(`/staples/preferences/${id}`)
}
