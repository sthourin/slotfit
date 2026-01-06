/**
 * Equipment API service
 */
import { apiClient } from './api'
import type { Equipment } from './api'

export type { Equipment }

export const equipmentApi = {
  /**
   * List all equipment
   */
  list: async (): Promise<Equipment[]> => {
    const response = await apiClient.get<Equipment[]>('/equipment/')
    return response.data
  },

  /**
   * Get a single equipment by ID
   */
  get: async (id: number): Promise<Equipment> => {
    const response = await apiClient.get<Equipment>(`/equipment/${id}`)
    return response.data
  },
}
