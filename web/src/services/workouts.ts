/**
 * Workout API service
 */
import { apiClient } from './api'

export type WorkoutState = 'draft' | 'active' | 'paused' | 'completed' | 'abandoned'
export type SlotState = 'not_started' | 'in_progress' | 'completed' | 'skipped'

export interface WorkoutSet {
  id: number
  workout_exercise_id: number
  set_number: number
  reps: number | null
  weight: number | null
  rest_seconds: number | null
  notes: string | null
}

export interface WorkoutExercise {
  id: number
  workout_session_id: number
  slot_id: number | null
  exercise_id: number
  slot_state: SlotState
  started_at: string | null // ISO date string
  stopped_at: string | null // ISO date string
  sets: WorkoutSet[]
}

export interface WorkoutSession {
  id: number
  routine_template_id: number | null
  state: WorkoutState
  started_at: string | null // ISO date string
  paused_at: string | null // ISO date string
  completed_at: string | null // ISO date string
  exercises: WorkoutExercise[]
}

export interface WorkoutSessionListResponse {
  workouts: WorkoutSession[]
  total: number
}

export interface WorkoutSessionCreate {
  routine_template_id?: number | null
  state?: WorkoutState
}

export interface WorkoutSessionUpdate {
  routine_template_id?: number | null
  state?: WorkoutState
}

export interface WorkoutSetCreate {
  set_number: number
  reps?: number | null
  weight?: number | null
  rest_seconds?: number | null
  notes?: string | null
}

export interface WorkoutSetUpdate {
  reps?: number | null
  weight?: number | null
  rest_seconds?: number | null
  notes?: string | null
}

export const workoutApi = {
  /**
   * List all workout sessions
   */
  list: async (params?: { skip?: number; limit?: number }): Promise<WorkoutSessionListResponse> => {
    const response = await apiClient.get<WorkoutSessionListResponse>('/workouts/', { params })
    return response.data
  },

  /**
   * Get a single workout session by ID
   */
  get: async (id: number): Promise<WorkoutSession> => {
    const response = await apiClient.get<WorkoutSession>(`/workouts/${id}`)
    return response.data
  },

  /**
   * Create a new workout session
   */
  create: async (data: WorkoutSessionCreate): Promise<WorkoutSession> => {
    const response = await apiClient.post<WorkoutSession>('/workouts/', data)
    return response.data
  },

  /**
   * Update an existing workout session
   */
  update: async (id: number, data: WorkoutSessionUpdate): Promise<WorkoutSession> => {
    const response = await apiClient.put<WorkoutSession>(`/workouts/${id}`, data)
    return response.data
  },

  /**
   * Delete a workout session
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/workouts/${id}`)
  },

  /**
   * Start a workout session
   */
  start: async (id: number): Promise<WorkoutSession> => {
    const response = await apiClient.post<WorkoutSession>(`/workouts/${id}/start`)
    return response.data
  },

  /**
   * Pause a workout session
   */
  pause: async (id: number): Promise<WorkoutSession> => {
    const response = await apiClient.post<WorkoutSession>(`/workouts/${id}/pause`)
    return response.data
  },

  /**
   * Complete a workout session
   */
  complete: async (id: number): Promise<WorkoutSession> => {
    const response = await apiClient.post<WorkoutSession>(`/workouts/${id}/complete`)
    return response.data
  },

  /**
   * Abandon a workout session
   */
  abandon: async (id: number): Promise<WorkoutSession> => {
    const response = await apiClient.post<WorkoutSession>(`/workouts/${id}/abandon`)
    return response.data
  },
}
