/**
 * Analytics API service
 */
import { apiClient } from './api'

export interface WeeklyVolumeMuscleGroup {
  muscle_group_id: number
  name: string
  total_sets: number
  total_reps: number
  total_volume: number
}

export interface WeeklyVolumeResponse {
  week_start: string // ISO date string (Monday)
  muscle_groups: WeeklyVolumeMuscleGroup[]
}

export interface SlotPerformanceMetric {
  slot_id: number
  slot_name: string | null
  completion_rate: number // 0.0-1.0
  average_sets: number
  most_used_exercise_id: number | null
  most_used_exercise_name: string | null
  times_performed: number
}

export interface SlotPerformanceResponse {
  routine_id: number
  routine_name: string
  slots: SlotPerformanceMetric[]
}

export interface ExerciseProgressionData {
  exercise_id: number
  exercise_name: string
  personal_records: Array<{
    id: number
    record_type: 'weight' | 'reps' | 'volume' | 'time'
    value: number
    context: Record<string, any> | null
    achieved_at: string // ISO date string
  }>
  recent_workouts: Array<{
    workout_id: number
    workout_date: string // ISO date string
    sets: Array<{
      set_number: number
      reps: number | null
      weight: number | null
    }>
  }>
}

export const analyticsApi = {
  /**
   * Get weekly volume data for all muscle groups for a given week
   * 
   * Returns volume metrics (sets, reps, total volume) per muscle group.
   * If weekStart is not provided, defaults to the current week's Monday.
   * week_start must be a Monday (ISO week start).
   */
  getWeeklyVolume: async (weekStart?: string): Promise<WeeklyVolumeResponse> => {
    const params: any = {}
    if (weekStart) {
      params.week_start = weekStart
    }
    const response = await apiClient.get<WeeklyVolumeResponse>('/analytics/weekly-volume', {
      params,
    })
    return response.data
  },

  /**
   * Get performance metrics for slots in a routine
   * 
   * Returns completion rates, average sets, most used exercises per slot.
   */
  getSlotPerformance: async (routineId: number): Promise<SlotPerformanceResponse> => {
    const response = await apiClient.get<SlotPerformanceResponse>('/analytics/slot-performance', {
      params: { routine_id: routineId },
    })
    return response.data
  },

  /**
   * Get progression data for a specific exercise
   * 
   * Returns personal records and recent workout history.
   */
  getExerciseProgression: async (exerciseId: number): Promise<ExerciseProgressionData> => {
    const response = await apiClient.get<ExerciseProgressionData>(
      `/analytics/exercise-progression/${exerciseId}`
    )
    return response.data
  },
}
