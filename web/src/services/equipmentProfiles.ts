/**
 * Equipment Profile API service
 */
import { apiClient } from './api'

export interface EquipmentProfile {
  id: number
  name: string
  equipment_ids: number[]
  is_default: boolean
  created_at: string // ISO date string
  updated_at: string // ISO date string
}

export interface EquipmentProfileCreate {
  name: string
  equipment_ids: number[]
  is_default?: boolean
}

export interface EquipmentProfileUpdate {
  name?: string
  equipment_ids?: number[]
  is_default?: boolean
}

export const equipmentProfileApi = {
  /**
   * List all equipment profiles
   */
  list: async (): Promise<EquipmentProfile[]> => {
    const response = await apiClient.get<EquipmentProfile[]>('/equipment-profiles/')
    return response.data
  },

  /**
   * Get a single equipment profile by ID
   */
  get: async (id: number): Promise<EquipmentProfile> => {
    const response = await apiClient.get<EquipmentProfile>(`/equipment-profiles/${id}`)
    return response.data
  },

  /**
   * Create a new equipment profile
   */
  create: async (data: EquipmentProfileCreate): Promise<EquipmentProfile> => {
    const response = await apiClient.post<EquipmentProfile>('/equipment-profiles/', data)
    return response.data
  },

  /**
   * Update an existing equipment profile
   */
  update: async (id: number, data: EquipmentProfileUpdate): Promise<EquipmentProfile> => {
    const response = await apiClient.put<EquipmentProfile>(`/equipment-profiles/${id}`, data)
    return response.data
  },

  /**
   * Delete an equipment profile
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/equipment-profiles/${id}`)
  },

  /**
   * Set an equipment profile as the default
   * This will clear is_default on all other profiles first
   */
  setDefault: async (id: number): Promise<EquipmentProfile> => {
    const response = await apiClient.post<EquipmentProfile>(`/equipment-profiles/${id}/set-default`)
    return response.data
  },
}
