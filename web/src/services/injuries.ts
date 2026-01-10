/**
 * Injury API service
 */
import { apiClient } from './api'

export interface InjuryType {
  id: number
  name: string
  body_area: string
  description: string | null
}

export interface InjuryTypeDetail extends InjuryType {
  severity_levels: string[]
  restrictions: MovementRestriction[]
}

export interface MovementRestriction {
  id: number
  restriction_type: string
  restriction_value: string
  severity_threshold: string
}

export interface UserInjury {
  id: number
  injury_type_id: number
  injury_type: InjuryType
  severity: 'mild' | 'moderate' | 'severe'
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserInjuryCreate {
  injury_type_id: number
  severity: 'mild' | 'moderate' | 'severe'
  notes?: string | null
}

export interface UserInjuryUpdate {
  severity?: 'mild' | 'moderate' | 'severe'
  notes?: string | null
  is_active?: boolean
}

export const injuryApi = {
  /**
   * List all injury types, optionally filtered by body area
   */
  listInjuryTypes: async (bodyArea?: string): Promise<InjuryType[]> => {
    const response = await apiClient.get<InjuryType[]>('/injury-types', {
      params: bodyArea ? { body_area: bodyArea } : {},
    })
    return response.data
  },

  /**
   * Get a single injury type with details
   */
  getInjuryType: async (id: number): Promise<InjuryTypeDetail> => {
    const response = await apiClient.get<InjuryTypeDetail>(`/injury-types/${id}`)
    return response.data
  },

  /**
   * List user's injuries
   */
  listUserInjuries: async (activeOnly: boolean = true): Promise<UserInjury[]> => {
    const response = await apiClient.get<UserInjury[]>('/user-injuries', {
      params: { active_only: activeOnly },
    })
    return response.data
  },

  /**
   * Add an injury to user's profile
   */
  addUserInjury: async (data: UserInjuryCreate): Promise<UserInjury> => {
    const response = await apiClient.post<UserInjury>('/user-injuries', data)
    return response.data
  },

  /**
   * Update user injury
   */
  updateUserInjury: async (id: number, data: UserInjuryUpdate): Promise<UserInjury> => {
    const response = await apiClient.put<UserInjury>(`/user-injuries/${id}`, data)
    return response.data
  },

  /**
   * Delete user injury
   */
  deleteUserInjury: async (id: number): Promise<void> => {
    await apiClient.delete(`/user-injuries/${id}`)
  },
}
