/**
 * UI Store - Modals, toasts, theme management
 */
import { create } from 'zustand'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  type: ToastType
  message: string
  duration?: number // milliseconds, default 3000
}

export type Theme = 'light' | 'dark' | 'system'

interface ModalState {
  isOpen: boolean
  data?: unknown
}

interface UIStore {
  // Theme
  theme: Theme
  setTheme: (theme: Theme) => void
  
  // Modals
  modals: {
    exerciseSelector: ModalState
    workoutStart: ModalState
    workoutComplete: ModalState
    equipmentProfileEditor: ModalState
    slotTemplateSelector: ModalState
    [key: string]: ModalState // Allow custom modals
  }
  
  openModal: (modalName: string, data?: unknown) => void
  closeModal: (modalName: string) => void
  closeAllModals: () => void
  
  // Toasts
  toasts: Toast[]
  showToast: (type: ToastType, message: string, duration?: number) => void
  removeToast: (id: string) => void
  clearToasts: () => void
  
  // Sidebar/Drawer state
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  toggleSidebar: () => void
}

let toastIdCounter = 0

export const useUIStore = create<UIStore>((set, get) => ({
  // Theme
  theme: (localStorage.getItem('slotfit-theme') as Theme) || 'system',
  setTheme: (theme: Theme) => {
    localStorage.setItem('slotfit-theme', theme)
    set({ theme })
    
    // Apply theme to document
    if (theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  },

  // Modals
  modals: {
    exerciseSelector: { isOpen: false },
    workoutStart: { isOpen: false },
    workoutComplete: { isOpen: false },
    equipmentProfileEditor: { isOpen: false },
    slotTemplateSelector: { isOpen: false },
  },

  openModal: (modalName: string, data?: unknown) => {
    set((state) => ({
      modals: {
        ...state.modals,
        [modalName]: {
          isOpen: true,
          data,
        },
      },
    }))
  },

  closeModal: (modalName: string) => {
    set((state) => ({
      modals: {
        ...state.modals,
        [modalName]: {
          isOpen: false,
          data: undefined,
        },
      },
    }))
  },

  closeAllModals: () => {
    set((state) => {
      const closedModals: typeof state.modals = {
        exerciseSelector: { isOpen: false },
        workoutStart: { isOpen: false },
        workoutComplete: { isOpen: false },
        equipmentProfileEditor: { isOpen: false },
        slotTemplateSelector: { isOpen: false },
      }
      // Close any custom modals
      Object.keys(state.modals).forEach((key) => {
        if (!closedModals[key as keyof typeof closedModals]) {
          closedModals[key] = { isOpen: false, data: undefined }
        }
      })
      return { modals: closedModals }
    })
  },

  // Toasts
  toasts: [],
  
  showToast: (type: ToastType, message: string, duration = 3000) => {
    const id = `toast-${++toastIdCounter}`
    const toast: Toast = { id, type, message, duration }
    
    set((state) => ({
      toasts: [...state.toasts, toast],
    }))
    
    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        get().removeToast(id)
      }, duration)
    }
  },

  removeToast: (id: string) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }))
  },

  clearToasts: () => {
    set({ toasts: [] })
  },

  // Sidebar
  sidebarOpen: false,
  setSidebarOpen: (open: boolean) => {
    set({ sidebarOpen: open })
  },
  
  toggleSidebar: () => {
    set((state) => ({ sidebarOpen: !state.sidebarOpen }))
  },
}))

// Initialize theme on store creation
if (typeof window !== 'undefined') {
  const storedTheme = localStorage.getItem('slotfit-theme') as Theme
  const theme = storedTheme || 'system'
  
  if (theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark')
  }
  
  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    const currentTheme = useUIStore.getState().theme
    if (currentTheme === 'system') {
      if (e.matches) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    }
  })
}
