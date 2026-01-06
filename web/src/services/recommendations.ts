/**
 * Recommendations API service
 */
import { apiClient } from './api'

export type RecordType = 'weight' | 'reps' | 'volume' | 'time'

export interface ExerciseRecommendation {
  exercise_id: number
  exercise_name: string
  priority_score: number // 0.0-1.0
  reasoning: string
  factors: {
    frequency?: string
    last_performed?: string
    progression_opportunity?: boolean
    variety_boost?: boolean
    movement_balance?: string
    weekly_volume_status?: string
    [key: string]: any
  }
}

export interface RecommendationResponse {
  recommendations: ExerciseRecommendation[]
  total_candidates: number
  filtered_by_equipment: number
  provider?: string | null // "claude", "fallback", etc.
}

export interface RecommendationParams {
  muscle_group_ids: number[]
  available_equipment_ids: number[]
  workout_session_id?: number | null
  limit?: number // Default: 5, max: 20
  use_cache?: boolean // Default: true
}

export const recommendationApi = {
  /**
   * Get AI-powered exercise recommendations for a slot
   * 
   * Returns top exercises prioritized based on:
   * - Muscle group targeting
   * - Equipment availability
   * - User workout history (if available)
   * - Workout variety
   * - Movement pattern balance (push/pull, compound/isolation)
   */
  getRecommendations: async (params: RecommendationParams): Promise<RecommendationResponse> => {
    const queryParams: any = {
      muscle_group_ids: params.muscle_group_ids,
      available_equipment_ids: params.available_equipment_ids,
      limit: params.limit ?? 5,
      use_cache: params.use_cache ?? true,
    }
    
    if (params.workout_session_id !== undefined && params.workout_session_id !== null) {
      queryParams.workout_session_id = params.workout_session_id
    }
    
    const response = await apiClient.get<RecommendationResponse>('/recommendations/', {
      params: queryParams,
    })
    return response.data
  },
}
