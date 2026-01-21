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
  rpe: number | null  // Rate of Perceived Exertion (1-10 scale)
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
  tags: Array<{ id: number; name: string; category: string | null }>
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
  rpe?: number | null  // Rate of Perceived Exertion (1-10 scale)
  notes?: string | null
}

export interface WorkoutSetUpdate {
  set_number?: number
  reps?: number | null
  weight?: number | null
  rest_seconds?: number | null
  rpe?: number | null  // Rate of Perceived Exertion (1-10 scale)
  notes?: string | null
}

export interface WorkoutExerciseUpdate {
  slot_state?: SlotState
  started_at?: string | null  // ISO date string
  stopped_at?: string | null  // ISO date string
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

  /**
   * Add an exercise to a workout slot
   */
  addExercise: async (
    workoutId: number,
    data: { routine_slot_id: number; exercise_id: number }
  ): Promise<WorkoutExercise> => {
    const response = await apiClient.post<WorkoutExercise>(
      `/workouts/${workoutId}/exercises`,
      data
    )
    return response.data
  },

  /**
   * Add a tag to a workout
   */
  addTag: async (workoutId: number, tagName: string): Promise<void> => {
    await apiClient.post(`/tags/workouts/${workoutId}/tags?tag_name=${encodeURIComponent(tagName)}`)
  },

  /**
   * Remove a tag from a workout
   */
  removeTag: async (workoutId: number, tagId: number): Promise<void> => {
    await apiClient.delete(`/tags/workouts/${workoutId}/tags/${tagId}`)
  },

  /**
   * Update a workout exercise (state, timestamps)
   */
  updateExercise: async (
    workoutId: number,
    exerciseId: number,
    data: WorkoutExerciseUpdate
  ): Promise<WorkoutExercise> => {
    const response = await apiClient.put<WorkoutExercise>(
      `/workouts/${workoutId}/exercises/${exerciseId}`,
      data
    )
    return response.data
  },

  /**
   * Create a set for a workout exercise
   */
  createSet: async (
    workoutId: number,
    exerciseId: number,
    data: WorkoutSetCreate
  ): Promise<WorkoutSet> => {
    const response = await apiClient.post<WorkoutSet>(
      `/workouts/${workoutId}/exercises/${exerciseId}/sets`,
      data
    )
    return response.data
  },

  /**
   * Update a workout set
   */
  updateSet: async (
    workoutId: number,
    exerciseId: number,
    setId: number,
    data: WorkoutSetUpdate
  ): Promise<WorkoutSet> => {
    const response = await apiClient.put<WorkoutSet>(
      `/workouts/${workoutId}/exercises/${exerciseId}/sets/${setId}`,
      data
    )
    return response.data
  },

  /**
   * Delete a workout set
   */
  deleteSet: async (
    workoutId: number,
    exerciseId: number,
    setId: number
  ): Promise<void> => {
    await apiClient.delete(`/workouts/${workoutId}/exercises/${exerciseId}/sets/${setId}`)
  },
}
