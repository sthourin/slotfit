/**
 * Muscle Group API service
 */
import { apiClient } from './api'
import type { MuscleGroup } from './api'

export type { MuscleGroup }

export const muscleGroupApi = {
  /**
   * List all muscle groups
   */
  list: async (): Promise<MuscleGroup[]> => {
    const response = await apiClient.get<{ muscle_groups: MuscleGroup[] }>('/muscle-groups/')
    return response.data.muscle_groups
  },

  /**
   * Get a single muscle group by ID
   */
  get: async (id: number): Promise<MuscleGroup> => {
    const response = await apiClient.get<MuscleGroup>(`/muscle-groups/${id}`)
    return response.data
  },
}
