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

export interface ConditioningExercise {
  exercise_id: number
  name: string
  sets: number
  seconds: number
  meters: number
  /** Effective load x metres: a ruck earns this, an ergometer does not. */
  load_meters: number
  /** null when there is no distance - a plank is not slow. */
  pace_seconds_per_km: number | null
}

export interface WeeklyConditioningResponse {
  week_start: string // ISO date string (Monday)
  total_sets: number
  total_seconds: number
  total_meters: number
  load_meters: number
  pace_seconds_per_km: number | null
  by_exercise: ConditioningExercise[]
}

export interface SlotPerformanceMetric {
  slot_id: number
  slot_name: string | null
  slot_order: number
  total_workouts: number
  completed_count: number
  skipped_count: number
  completion_rate: number // 0.0-1.0
  avg_sets_per_workout: number
  most_used_exercise_id: number | null
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
    const params: { week_start?: string } = {}
    if (weekStart) {
      params.week_start = weekStart
    }
    const response = await apiClient.get<WeeklyVolumeResponse>('/analytics/weekly-volume', {
      params,
    })
    return response.data
  },

  /**
   * Get weekly conditioning data: sets, duration, distance, pace, load-distance.
   *
   * Deliberately a separate call from getWeeklyVolume. Tonnage and distance do
   * not share a unit, so they are reported side by side rather than summed -
   * one ruck would otherwise outweigh a month of lifting on the volume chart.
   */
  getWeeklyConditioning: async (weekStart?: string): Promise<WeeklyConditioningResponse> => {
    const params: { week_start?: string } = {}
    if (weekStart) {
      params.week_start = weekStart
    }
    const response = await apiClient.get<WeeklyConditioningResponse>(
      '/analytics/weekly-conditioning',
      { params }
    )
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
