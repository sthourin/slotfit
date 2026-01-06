/**
 * Central export point for all API services
 */
export * from './api'
export * from './exercises'
export * from './routines'
export * from './workouts'
export * from './equipmentProfiles'
export * from './slotTemplates'
export * from './analytics'
export * from './muscleGroups'
export * from './equipment'
export * from './personalRecords'

// Export recommendations types explicitly to avoid conflicts
export type {
  ExerciseRecommendation,
  RecommendationResponse,
  RecommendationParams,
} from './recommendations'

// Re-export API clients for convenience
export { exerciseApi } from './exercises'
export { routineApi } from './routines'
export { workoutApi } from './workouts'
export { equipmentProfileApi } from './equipmentProfiles'
export { slotTemplateApi } from './slotTemplates'
export { recommendationApi } from './recommendations'
export { analyticsApi } from './analytics'
export { muscleGroupApi } from './muscleGroups'
export { equipmentApi } from './equipment'
export { personalRecordApi } from './personalRecords'
