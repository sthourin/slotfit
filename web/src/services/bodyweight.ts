/**
 * Bodyweight readings API service
 */
import { apiClient } from './api'

export interface BodyweightReading {
  id: number
  weight: number
  recorded_at: string
  /** "manual" today; "health_connect" once that sync exists. */
  source: string
}

export async function listReadings(): Promise<BodyweightReading[]> {
  const { data } = await apiClient.get('/bodyweight')
  return data
}

export async function createReading(
  weight: number,
  recordedAt?: string
): Promise<BodyweightReading> {
  const { data } = await apiClient.post('/bodyweight', {
    weight,
    recorded_at: recordedAt ?? null,
  })
  return data
}

export async function deleteReading(id: number): Promise<void> {
  await apiClient.delete(`/bodyweight/${id}`)
}
