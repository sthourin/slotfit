import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiClient } from '../services/api'

interface User {
  id: number
  device_id: string | null
  display_name: string
  preferred_units: 'lbs' | 'kg'
  created_at: string
}

interface UserStore {
  user: User | null
  loading: boolean
  error: string | null
  
  // Actions
  fetchCurrentUser: () => Promise<void>
  updateProfile: (updates: { display_name?: string; preferred_units?: string }) => Promise<void>
  clearUser: () => void
}

export const useUserStore = create<UserStore>()(
  persist(
    (set, get) => ({
      user: null,
      loading: false,
      error: null,

      fetchCurrentUser: async () => {
        set({ loading: true, error: null })
        try {
          const response = await apiClient.get<User>('/users/me')
          set({ user: response.data, loading: false })
        } catch (error) {
          set({ error: (error as Error).message, loading: false })
        }
      },

      updateProfile: async (updates) => {
        set({ loading: true, error: null })
        try {
          const response = await apiClient.put<User>('/users/me', updates)
          set({ user: response.data, loading: false })
        } catch (error) {
          set({ error: (error as Error).message, loading: false })
        }
      },

      clearUser: () => {
        set({ user: null, error: null })
      },
    }),
    {
      name: 'slotfit-user',
      partialize: (state) => ({ user: state.user }),
    }
  )
)
