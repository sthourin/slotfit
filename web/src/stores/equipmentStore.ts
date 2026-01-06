/**
 * Equipment Store - Equipment profiles management
 */
import { create } from 'zustand'
import { equipmentProfileApi, type EquipmentProfile } from '../services/equipmentProfiles'

interface EquipmentStore {
  // State
  profiles: EquipmentProfile[]
  selectedProfileId: number | null
  defaultProfileId: number | null
  
  // Loading states
  loading: boolean
  saving: boolean
  
  // Actions
  loadProfiles: () => Promise<void>
  createProfile: (name: string, equipmentIds: number[], isDefault?: boolean) => Promise<void>
  updateProfile: (id: number, updates: { name?: string; equipmentIds?: number[]; isDefault?: boolean }) => Promise<void>
  deleteProfile: (id: number) => Promise<void>
  setDefaultProfile: (id: number) => Promise<void>
  selectProfile: (id: number | null) => void
  
  // Getters
  getSelectedProfile: () => EquipmentProfile | null
  getDefaultProfile: () => EquipmentProfile | null
}

export const useEquipmentStore = create<EquipmentStore>((set, get) => ({
  profiles: [],
  selectedProfileId: null,
  defaultProfileId: null,
  loading: false,
  saving: false,

  loadProfiles: async () => {
    set({ loading: true })
    try {
      const profiles = await equipmentProfileApi.list()
      const defaultProfile = profiles.find((p) => p.is_default)
      
      set({
        profiles,
        defaultProfileId: defaultProfile?.id ?? null,
        selectedProfileId: defaultProfile?.id ?? null,
        loading: false,
      })
    } catch (error) {
      console.error('Failed to load equipment profiles:', error)
      set({ loading: false })
      throw error
    }
  },

  createProfile: async (name: string, equipmentIds: number[], isDefault = false) => {
    set({ saving: true })
    try {
      const newProfile = await equipmentProfileApi.create({
        name,
        equipment_ids: equipmentIds,
        is_default: isDefault,
      })
      
      set((state) => ({
        profiles: [...state.profiles, newProfile],
        defaultProfileId: newProfile.is_default ? newProfile.id : state.defaultProfileId,
        selectedProfileId: newProfile.is_default ? newProfile.id : state.selectedProfileId,
        saving: false,
      }))
      
      // If this is set as default, update other profiles
      if (isDefault) {
        // The backend handles clearing other defaults, but we should reload to sync
        await get().loadProfiles()
      }
    } catch (error) {
      console.error('Failed to create equipment profile:', error)
      set({ saving: false })
      throw error
    }
  },

  updateProfile: async (id: number, updates: { name?: string; equipmentIds?: number[]; isDefault?: boolean }) => {
    set({ saving: true })
    try {
      const updateData: {
        name?: string
        equipment_ids?: number[]
        is_default?: boolean
      } = {}
      
      if (updates.name !== undefined) updateData.name = updates.name
      if (updates.equipmentIds !== undefined) updateData.equipment_ids = updates.equipmentIds
      if (updates.isDefault !== undefined) updateData.is_default = updates.isDefault
      
      const updated = await equipmentProfileApi.update(id, updateData)
      
      set((state) => ({
        profiles: state.profiles.map((p) => (p.id === id ? updated : p)),
        defaultProfileId: updated.is_default ? updated.id : (state.defaultProfileId === id ? null : state.defaultProfileId),
        selectedProfileId: state.selectedProfileId === id ? updated.id : state.selectedProfileId,
        saving: false,
      }))
      
      // If this was set as default, reload to sync other profiles
      if (updates.isDefault) {
        await get().loadProfiles()
      }
    } catch (error) {
      console.error('Failed to update equipment profile:', error)
      set({ saving: false })
      throw error
    }
  },

  deleteProfile: async (id: number) => {
    set({ saving: true })
    try {
      await equipmentProfileApi.delete(id)
      
      set((state) => {
        const newProfiles = state.profiles.filter((p) => p.id !== id)
        return {
          profiles: newProfiles,
          selectedProfileId: state.selectedProfileId === id ? null : state.selectedProfileId,
          defaultProfileId: state.defaultProfileId === id ? null : state.defaultProfileId,
          saving: false,
        }
      })
    } catch (error) {
      console.error('Failed to delete equipment profile:', error)
      set({ saving: false })
      throw error
    }
  },

  setDefaultProfile: async (id: number) => {
    set({ saving: true })
    try {
      await equipmentProfileApi.setDefault(id)
      
      set((state) => ({
        profiles: state.profiles.map((p) => ({
          ...p,
          is_default: p.id === id,
        })),
        defaultProfileId: id,
        selectedProfileId: id,
        saving: false,
      }))
    } catch (error) {
      console.error('Failed to set default equipment profile:', error)
      set({ saving: false })
      throw error
    }
  },

  selectProfile: (id: number | null) => {
    set({ selectedProfileId: id })
  },

  getSelectedProfile: () => {
    const { profiles, selectedProfileId } = get()
    return profiles.find((p) => p.id === selectedProfileId) ?? null
  },

  getDefaultProfile: () => {
    const { profiles, defaultProfileId } = get()
    return profiles.find((p) => p.id === defaultProfileId) ?? null
  },
}))
