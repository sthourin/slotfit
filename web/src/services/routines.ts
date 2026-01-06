/**
 * Routine API service
 */
import { apiClient } from './api'

export interface RoutineSlot {
  id: number
  routine_template_id: number
  name: string | null
  order: number
  muscle_group_ids: number[]
  superset_tag: string | null
  selected_exercise_id: number | null
  workout_style: string | null // Optional workout style for this slot (overrides routine workout_style)
  slot_type?: string // 'standard' | 'warmup' | 'finisher' | 'active_recovery' | 'wildcard'
  slot_template_id?: number | null
  time_limit_seconds?: number | null
  required_equipment_ids?: number[] | null
  target_reps_min?: number | null
  target_reps_max?: number | null
  progression_rule?: Record<string, any> | null
}

export interface RoutineTemplate {
  id: number
  name: string
  routine_type: string | null
  workout_style: string | null
  description: string | null
  slots: RoutineSlot[]
}

export interface RoutineTemplateListResponse {
  routines: RoutineTemplate[]
  total: number
}

export interface RoutineSlotCreate {
  name?: string | null
  order: number
  muscle_group_ids: number[]
  superset_tag?: string | null
  selected_exercise_id?: number | null
  workout_style?: string | null
  slot_type?: string
  slot_template_id?: number | null
  time_limit_seconds?: number | null
  required_equipment_ids?: number[] | null
  target_reps_min?: number | null
  target_reps_max?: number | null
  progression_rule?: Record<string, any> | null
}

export interface RoutineTemplateCreate {
  name: string
  routine_type?: string | null
  workout_style?: string | null
  description?: string | null
  slots?: RoutineSlotCreate[]
}

export interface RoutineTemplateUpdate {
  name?: string
  routine_type?: string | null
  workout_style?: string | null
  description?: string | null
}

export const routineApi = {
  /**
   * List all routine templates
   */
  list: async (params?: { skip?: number; limit?: number }): Promise<RoutineTemplateListResponse> => {
    const response = await apiClient.get<RoutineTemplateListResponse>('/routines/', { params })
    return response.data
  },

  /**
   * Get a single routine template by ID
   */
  get: async (id: number): Promise<RoutineTemplate> => {
    const response = await apiClient.get<RoutineTemplate>(`/routines/${id}`)
    return response.data
  },

  /**
   * Create a new routine template
   */
  create: async (data: RoutineTemplateCreate): Promise<RoutineTemplate> => {
    const response = await apiClient.post<RoutineTemplate>('/routines/', data)
    return response.data
  },

  /**
   * Update an existing routine template
   */
  update: async (id: number, data: RoutineTemplateUpdate): Promise<RoutineTemplate> => {
    const response = await apiClient.put<RoutineTemplate>(`/routines/${id}`, data)
    return response.data
  },

  /**
   * Delete a routine template
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/routines/${id}`)
  },

  /**
   * Add a slot to a routine template
   */
  addSlot: async (routineId: number, slot: RoutineSlotCreate): Promise<RoutineTemplate> => {
    const response = await apiClient.post<RoutineTemplate>(`/routines/${routineId}/slots`, slot)
    return response.data
  },

  /**
   * Update a slot in a routine template
   */
  updateSlot: async (
    routineId: number,
    slotId: number,
    slot: RoutineSlotCreate
  ): Promise<RoutineTemplate> => {
    const response = await apiClient.put<RoutineTemplate>(
      `/routines/${routineId}/slots/${slotId}`,
      slot
    )
    return response.data
  },

  /**
   * Delete a slot from a routine template
   */
  deleteSlot: async (routineId: number, slotId: number): Promise<RoutineTemplate> => {
    const response = await apiClient.delete<RoutineTemplate>(
      `/routines/${routineId}/slots/${slotId}`
    )
    return response.data
  },
}
