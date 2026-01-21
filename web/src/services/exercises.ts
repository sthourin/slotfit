/**
 * Exercise API service
 */
import { apiClient } from './api'
import type { MuscleGroup, Equipment } from './api'

export interface Exercise {
  id: number
  name: string
  description: string | null
  difficulty: 'Easy' | 'Intermediate' | 'Advanced' | null
  exercise_classification: string | null
  short_demo_url: string | null
  in_depth_url: string | null
  primary_equipment: Equipment | null
  secondary_equipment: Equipment | null
  primary_equipment_count: number
  secondary_equipment_count: number
  muscle_groups: MuscleGroup[]
  posture: string | null
  movement_pattern_1: string | null
  movement_pattern_2: string | null
  movement_pattern_3: string | null
  body_region: string | null
  force_type: string | null
  mechanics: string | null
  laterality: string | null
  last_performed: string | null // ISO date string
  // Variant fields
  base_exercise_id: number | null
  variant_type: string | null // "HIIT", "Strength", "Volume", "Endurance", "Custom"
  is_custom: boolean
  default_sets: number | null
  default_reps: number | null
  default_weight: number | null
  default_time_seconds: number | null
  default_rest_seconds: number | null
  tags: Array<{ id: number; name: string; category: string | null }>
}

export interface ExerciseListResponse {
  exercises: Exercise[]
  total: number
  page: number
  page_size: number
}

export interface ExerciseCreate {
  name: string
  description?: string | null
  difficulty?: 'Easy' | 'Intermediate' | 'Advanced' | null
  exercise_classification?: string | null
  short_demo_url?: string | null
  in_depth_url?: string | null
  primary_equipment_id?: number | null
  secondary_equipment_id?: number | null
  primary_equipment_count?: number
  secondary_equipment_count?: number
  muscle_group_ids?: number[]
  posture?: string | null
  movement_pattern_1?: string | null
  movement_pattern_2?: string | null
  movement_pattern_3?: string | null
  body_region?: string | null
  force_type?: string | null
  mechanics?: string | null
  laterality?: string | null
  variant_type?: string | null
  default_sets?: number | null
  default_reps?: number | null
  default_weight?: number | null
  default_time_seconds?: number | null
  default_rest_seconds?: number | null
}

export interface ExerciseUpdate {
  name?: string
  description?: string | null
  difficulty?: 'Easy' | 'Intermediate' | 'Advanced' | null
  exercise_classification?: string | null
  short_demo_url?: string | null
  in_depth_url?: string | null
  primary_equipment_id?: number | null
  secondary_equipment_id?: number | null
  primary_equipment_count?: number
  secondary_equipment_count?: number
  muscle_group_ids?: number[]
  posture?: string | null
  movement_pattern_1?: string | null
  movement_pattern_2?: string | null
  movement_pattern_3?: string | null
  body_region?: string | null
  force_type?: string | null
  mechanics?: string | null
  laterality?: string | null
  variant_type?: string | null
  default_sets?: number | null
  default_reps?: number | null
  default_weight?: number | null
  default_time_seconds?: number | null
  default_rest_seconds?: number | null
}

export interface ExerciseVariantCreate {
  name?: string
  variant_type: string
  default_sets?: number
  default_reps?: number
  default_weight?: number
  default_time_seconds?: number
  default_rest_seconds?: number
}

export const exerciseApi = {
  /**
   * List exercises with optional filters
   */
  list: async (params?: {
    skip?: number
    limit?: number
    search?: string
    muscle_group_id?: number
    muscle_group_ids?: number[] // Multiple muscle group IDs (for target role)
    secondary_muscle_group_ids?: number[] // Multiple muscle group IDs (for secondary role)
    tertiary_muscle_group_ids?: number[] // Multiple muscle group IDs (for tertiary role)
    equipment_id?: number
    difficulty?: string
    body_region?: string
    mechanics?: string
    routine_type?: 'anterior' | 'posterior' | 'full_body' | 'custom'
    workout_style?: '5x5' | 'HIIT' | 'volume' | 'strength' | 'custom'
    tag_ids?: number[] // Multiple tag IDs (AND logic - exercise must have all tags)
    variant_type?: string // Filter by variant type: "HIIT", "Strength", etc.
    base_exercise_id?: number // Get all variants of a base exercise
    include_variants?: boolean // Include exercise variants in results
    combination_only?: boolean // Filter to only combination exercises (multiple target muscle groups)
    sort_by?: 'name' | 'difficulty' | 'last_performed' | 'equipment'
    sort_order?: 'asc' | 'desc'
  }): Promise<ExerciseListResponse> => {
    // Convert muscle_group_ids, secondary_muscle_group_ids, tertiary_muscle_group_ids, and tag_ids arrays to comma-separated strings
    const apiParams: any = { ...params }
    if (apiParams.muscle_group_ids && Array.isArray(apiParams.muscle_group_ids)) {
      apiParams.muscle_group_ids = apiParams.muscle_group_ids.join(',')
      delete apiParams.muscle_group_id // Don't send both
    }
    if (apiParams.secondary_muscle_group_ids && Array.isArray(apiParams.secondary_muscle_group_ids)) {
      apiParams.secondary_muscle_group_ids = apiParams.secondary_muscle_group_ids.join(',')
    }
    if (apiParams.tertiary_muscle_group_ids && Array.isArray(apiParams.tertiary_muscle_group_ids)) {
      apiParams.tertiary_muscle_group_ids = apiParams.tertiary_muscle_group_ids.join(',')
    }
    if (apiParams.tag_ids && Array.isArray(apiParams.tag_ids)) {
      apiParams.tag_ids = apiParams.tag_ids.join(',')
    }
    const response = await apiClient.get<ExerciseListResponse>('/exercises/', { params: apiParams })
    return response.data
  },

  /**
   * Get a single exercise by ID
   */
  get: async (id: number): Promise<Exercise> => {
    const response = await apiClient.get<Exercise>(`/exercises/${id}`)
    return response.data
  },

  /**
   * Create a new exercise
   */
  create: async (data: ExerciseCreate): Promise<Exercise> => {
    const response = await apiClient.post<Exercise>('/exercises/', data)
    return response.data
  },

  /**
   * Update an existing exercise
   */
  update: async (id: number, data: ExerciseUpdate): Promise<Exercise> => {
    const response = await apiClient.put<Exercise>(`/exercises/${id}`, data)
    return response.data
  },

  /**
   * Delete an exercise
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/exercises/${id}`)
  },

  /**
   * Get all variants of an exercise
   */
  getVariants: async (exerciseId: number): Promise<ExerciseListResponse> => {
    const response = await apiClient.get<ExerciseListResponse>(`/exercises/${exerciseId}/variants`)
    return response.data
  },

  /**
   * Create a variant (duplicate) of an exercise
   */
  duplicate: async (exerciseId: number, variantData: ExerciseVariantCreate): Promise<Exercise> => {
    const response = await apiClient.post<Exercise>(`/exercises/${exerciseId}/duplicate`, variantData)
    return response.data
  },
}
