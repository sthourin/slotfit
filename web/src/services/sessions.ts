/**
 * Training session API service
 */
import axios from 'axios'
import { apiClient } from './api'

export interface Target {
  weight: number | null
  /** null for time-only work, which gets no rep prescription. */
  reps: number | null
  sets: number
  time_seconds: number | null
  distance_meters: number | null
  /**
   * 'target' = do exactly this many reps; 'beat' = exceed this many (AMRAP);
   * null = no rep prescription at all.
   */
  reps_goal: 'target' | 'beat' | null
  /**
   * How to read time_seconds / distance_meters on a conditioning target.
   * 'beat_time' = cover distance_meters faster; 'beat_distance' = cover more
   * ground within time_seconds; null = the numbers describe the last
   * performance and prescribe nothing.
   */
  pace_goal: 'beat_time' | 'beat_distance' | null
  last_summary: string | null
}

export interface EntrySet {
  id: number
  entry_id: number
  set_number: number
  weight: number | null
  reps: number | null
  time_seconds: number | null
  /** Metres. The unit every ergometer reports and what Hevy exports. */
  distance_meters: number | null
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
  set_protocol: 'reps' | 'time' | 'amrap' | 'emom' | 'distance'
  /** Drives the "+ weight" label: on these, weight means ADDED load. */
  is_bodyweight: boolean
  default_time_seconds: number | null
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

/**
 * Returns the active session, or null when there genuinely is none (404).
 *
 * Any other failure -- a 500, a dropped connection mid-workout -- is re-thrown.
 * Swallowing those rendered "No active session" while a session was in fact
 * live, and the user's attempt to start a fresh one then 409'd with nothing on
 * screen to explain it.
 */
export async function getActiveSession(): Promise<TrainingSession | null> {
  try {
    const { data } = await apiClient.get('/sessions/active')
    return data
  } catch (e) {
    if (axios.isAxiosError(e) && e.response?.status === 404) return null
    throw e
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
  set: {
    set_number: number
    weight?: number | null
    reps?: number | null
    time_seconds?: number | null
    distance_meters?: number | null
  }
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
