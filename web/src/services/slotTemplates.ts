/**
 * Slot Template API service
 */
import { apiClient } from './api'

export type SlotType = 'standard' | 'warmup' | 'finisher' | 'active_recovery' | 'wildcard'

export interface SlotTemplate {
  id: number
  name: string
  slot_type: SlotType
  muscle_group_ids: number[]
  time_limit_seconds: number | null
  default_exercise_id: number | null
  target_sets: number | null
  target_reps_min: number | null
  target_reps_max: number | null
  target_weight: number | null
  target_rest_seconds: number | null
  notes: string | null
  created_at: string // ISO date string
  updated_at: string // ISO date string
}

export interface SlotTemplateCreate {
  name: string
  slot_type?: SlotType
  muscle_group_ids: number[]
  time_limit_seconds?: number | null
  default_exercise_id?: number | null
  target_sets?: number | null
  target_reps_min?: number | null
  target_reps_max?: number | null
  target_weight?: number | null
  target_rest_seconds?: number | null
  notes?: string | null
}

export interface SlotTemplateUpdate {
  name?: string
  slot_type?: SlotType
  muscle_group_ids?: number[]
  time_limit_seconds?: number | null
  default_exercise_id?: number | null
  target_sets?: number | null
  target_reps_min?: number | null
  target_reps_max?: number | null
  target_weight?: number | null
  target_rest_seconds?: number | null
  notes?: string | null
}

export const slotTemplateApi = {
  /**
   * List all slot templates, optionally filtered by slot_type
   */
  list: async (params?: { slot_type?: SlotType }): Promise<SlotTemplate[]> => {
    const response = await apiClient.get<SlotTemplate[]>('/slot-templates/', { params })
    return response.data
  },

  /**
   * Get a single slot template by ID
   */
  get: async (id: number): Promise<SlotTemplate> => {
    const response = await apiClient.get<SlotTemplate>(`/slot-templates/${id}`)
    return response.data
  },

  /**
   * Create a new slot template
   */
  create: async (data: SlotTemplateCreate): Promise<SlotTemplate> => {
    const response = await apiClient.post<SlotTemplate>('/slot-templates/', data)
    return response.data
  },

  /**
   * Update an existing slot template
   */
  update: async (id: number, data: SlotTemplateUpdate): Promise<SlotTemplate> => {
    const response = await apiClient.put<SlotTemplate>(`/slot-templates/${id}`, data)
    return response.data
  },

  /**
   * Delete a slot template
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/slot-templates/${id}`)
  },
}
