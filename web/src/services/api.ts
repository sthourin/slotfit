/**
 * API client configuration
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add response interceptor for better error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Improve error messages
    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      error.message = 'Network Error: Cannot connect to server. Please ensure the backend is running at http://localhost:8000'
    } else if (error.response) {
      // Server responded with error status
      error.message = error.response.data?.detail || error.response.data?.message || error.message
    }
    return Promise.reject(error)
  }
)

// Types
export interface Exercise {
  id: number
  name: string
  description: string | null
  difficulty: 'Beginner' | 'Novice' | 'Intermediate' | 'Advanced' | 'Expert' | null
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
  last_performed: string | null  // ISO date string
  // Variant fields
  base_exercise_id: number | null
  variant_type: string | null  // "HIIT", "Strength", "Volume", "Endurance", "Custom"
  is_custom: boolean
  default_sets: number | null
  default_reps: number | null
  default_weight: number | null
  default_time_seconds: number | null
  default_rest_seconds: number | null
}

export interface MuscleGroup {
  id: number
  name: string
  level: number
  parent_id: number | null
}

export interface Equipment {
  id: number
  name: string
  category: string | null
}

export interface ExerciseListResponse {
  exercises: Exercise[]
  total: number
  page: number
  page_size: number
}

// Routine Types
export interface RoutineSlot {
  id: number
  routine_template_id: number
  name: string | null
  order: number
  muscle_group_ids: number[]
  superset_tag: string | null
  selected_exercise_id: number | null
  workout_style: string | null  // Optional workout style for this slot (overrides routine workout_style)
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
  order: number
  muscle_group_ids: number[]
  superset_tag?: string | null
  selected_exercise_id?: number | null
  workout_style?: string | null  // Optional workout style for this slot
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

// API functions
export const exerciseApi = {
  list: async (params?: {
    skip?: number
    limit?: number
    search?: string
    muscle_group_id?: number
    muscle_group_ids?: number[]  // Multiple muscle group IDs
    equipment_id?: number
    difficulty?: string
    body_region?: string
    mechanics?: string
    routine_type?: 'anterior' | 'posterior' | 'full_body' | 'custom'
    workout_style?: '5x5' | 'HIIT' | 'volume' | 'strength' | 'custom'
    variant_type?: string  // Filter by variant type: "HIIT", "Strength", etc.
    base_exercise_id?: number  // Get all variants of a base exercise
    include_variants?: boolean  // Include exercise variants in results
    sort_by?: 'name' | 'difficulty' | 'last_performed' | 'equipment'
    sort_order?: 'asc' | 'desc'
  }): Promise<ExerciseListResponse> => {
    // Convert muscle_group_ids array to comma-separated string
    const apiParams: any = { ...params }
    if (apiParams.muscle_group_ids && Array.isArray(apiParams.muscle_group_ids)) {
      apiParams.muscle_group_ids = apiParams.muscle_group_ids.join(',')
      delete apiParams.muscle_group_id  // Don't send both
    }
    const response = await apiClient.get<ExerciseListResponse>('/exercises/', { params: apiParams })
    return response.data
  },
  
  getVariants: async (exerciseId: number): Promise<ExerciseListResponse> => {
    const response = await apiClient.get<ExerciseListResponse>(`/exercises/${exerciseId}/variants`)
    return response.data
  },
  
  duplicate: async (exerciseId: number, variantData: {
    name?: string
    variant_type: string
    default_sets?: number
    default_reps?: number
    default_weight?: number
    default_time_seconds?: number
    default_rest_seconds?: number
  }): Promise<Exercise> => {
    const response = await apiClient.post<Exercise>(`/exercises/${exerciseId}/duplicate`, variantData)
    return response.data
  },

  get: async (id: number): Promise<Exercise> => {
    const response = await apiClient.get<Exercise>(`/exercises/${id}`)
    return response.data
  },
}

export const muscleGroupApi = {
  list: async (): Promise<MuscleGroup[]> => {
    const response = await apiClient.get<{ muscle_groups: MuscleGroup[] }>('/muscle-groups/')
    return response.data.muscle_groups
  },
}

export const equipmentApi = {
  list: async (): Promise<Equipment[]> => {
    // TODO: Create equipment endpoint in backend
    // For now, extract from exercises
    const exercises = await exerciseApi.list({ limit: 1000 })
    const equipment = new Map<number, Equipment>()
    exercises.exercises.forEach(ex => {
      if (ex.primary_equipment && !equipment.has(ex.primary_equipment.id)) {
        equipment.set(ex.primary_equipment.id, ex.primary_equipment)
      }
      if (ex.secondary_equipment && !equipment.has(ex.secondary_equipment.id)) {
        equipment.set(ex.secondary_equipment.id, ex.secondary_equipment)
      }
    })
    return Array.from(equipment.values())
  },
}

export const routineApi = {
  list: async (params?: { skip?: number; limit?: number }): Promise<RoutineTemplateListResponse> => {
    const response = await apiClient.get<RoutineTemplateListResponse>('/routines/', { params })
    return response.data
  },

  get: async (id: number): Promise<RoutineTemplate> => {
    const response = await apiClient.get<RoutineTemplate>(`/routines/${id}`)
    return response.data
  },

  create: async (data: RoutineTemplateCreate): Promise<RoutineTemplate> => {
    const response = await apiClient.post<RoutineTemplate>('/routines/', data)
    return response.data
  },

  update: async (id: number, data: RoutineTemplateUpdate): Promise<RoutineTemplate> => {
    const response = await apiClient.put<RoutineTemplate>(`/routines/${id}`, data)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/routines/${id}`)
  },

  addSlot: async (routineId: number, slot: RoutineSlotCreate): Promise<RoutineTemplate> => {
    const response = await apiClient.post<RoutineTemplate>(
      `/routines/${routineId}/slots`,
      slot
    )
    return response.data
  },

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

  deleteSlot: async (routineId: number, slotId: number): Promise<RoutineTemplate> => {
    const response = await apiClient.delete<RoutineTemplate>(
      `/routines/${routineId}/slots/${slotId}`
    )
    return response.data
  },
}
