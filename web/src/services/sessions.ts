/**
 * Training session API service
 */
import { apiClient } from './api'

export interface Target {
  weight: number | null
  reps: number
  sets: number
  last_summary: string | null
}

export interface EntrySet {
  id: number
  entry_id: number
  set_number: number
  weight: number | null
  reps: number | null
  time_seconds: number | null
  completed: boolean
}

export interface RoundEntry {
  id: number
  round_id: number
  position: number
  exercise_id: number
  exercise_name: string
  pattern_id: number
  pattern_slug: string
  sets: EntrySet[]
  target: Target | null
}

export interface SupersetRound {
  id: number
  session_id: number
  order: number
  entries: RoundEntry[]
}

export interface TrainingSession {
  id: number
  day_plan_id: number | null
  state: 'draft' | 'active' | 'completed' | 'discarded'
  started_at: string | null
  completed_at: string | null
  notes: string | null
  rounds: SupersetRound[]
}

export interface CoverageGoal {
  pattern_id: number
  slug: string
  name: string
  required: boolean
  target_sets: number
  sets_done: number
  covered: boolean
}

export interface Coverage {
  goals: CoverageGoal[]
}

export async function createSession(dayPlanId: number | null): Promise<TrainingSession> {
  const { data } = await apiClient.post('/sessions/', { day_plan_id: dayPlanId })
  return data
}

export async function getActiveSession(): Promise<TrainingSession | null> {
  try {
    const { data } = await apiClient.get('/sessions/active')
    return data
  } catch {
    return null
  }
}

export async function getSession(id: number): Promise<TrainingSession> {
  const { data } = await apiClient.get(`/sessions/${id}`)
  return data
}

export async function listSessions(state?: string, limit = 20): Promise<TrainingSession[]> {
  const { data } = await apiClient.get('/sessions/', { params: { state, limit } })
  return data
}

export async function createRound(sessionId: number): Promise<SupersetRound> {
  const { data } = await apiClient.post(`/sessions/${sessionId}/rounds`)
  return data
}

export async function createEntry(roundId: number, exerciseId: number, position: number): Promise<RoundEntry> {
  const { data } = await apiClient.post(`/sessions/rounds/${roundId}/entries`, {
    exercise_id: exerciseId,
    position,
  })
  return data
}

export async function createSet(
  entryId: number,
  set: { set_number: number; weight?: number | null; reps?: number | null; time_seconds?: number | null }
): Promise<EntrySet> {
  const { data } = await apiClient.post(`/sessions/entries/${entryId}/sets`, set)
  return data
}

export async function completeSession(id: number): Promise<TrainingSession> {
  const { data } = await apiClient.post(`/sessions/${id}/complete`)
  return data
}

export async function discardSession(id: number): Promise<TrainingSession> {
  const { data } = await apiClient.post(`/sessions/${id}/discard`)
  return data
}

export async function getCoverage(sessionId: number): Promise<Coverage> {
  const { data } = await apiClient.get(`/sessions/${sessionId}/coverage`)
  return data
}
