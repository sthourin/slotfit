/**
 * Personal Records API service
 */
import { apiClient } from './api'

export type RecordType = 'weight' | 'reps' | 'volume' | 'time'

export interface PersonalRecord {
  id: number
  exercise_id: number
  record_type: RecordType
  value: number
  context: Record<string, any> | null
  achieved_at: string // ISO date string
  workout_session_id: number | null
}

export interface PersonalRecordListResponse {
  records: PersonalRecord[]
  total: number
}

export interface PersonalRecordCreate {
  exercise_id: number
  record_type: RecordType
  value: number
  context?: Record<string, any> | null
  achieved_at: string // ISO date string
  workout_session_id?: number | null
}

export const personalRecordApi = {
  /**
   * List all personal records, optionally filtered by exercise_id
   */
  list: async (params?: { exercise_id?: number }): Promise<PersonalRecordListResponse> => {
    const response = await apiClient.get<PersonalRecordListResponse>('/personal-records/', {
      params,
    })
    return response.data
  },

  /**
   * Get personal records for a specific exercise
   */
  getByExercise: async (exerciseId: number): Promise<PersonalRecordListResponse> => {
    const response = await apiClient.get<PersonalRecordListResponse>(
      `/personal-records/exercise/${exerciseId}`
    )
    return response.data
  },
}
