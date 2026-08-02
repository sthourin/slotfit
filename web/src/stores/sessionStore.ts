/**
 * Training session store using Zustand
 *
 * The server is the source of truth for session state: every mutating action
 * re-fetches the session (and coverage where applicable) rather than
 * optimistically patching local state, because the backend computes derived
 * data (progression targets, pattern coverage) that the client cannot.
 */
import { create } from 'zustand'
import {
  createSession, getActiveSession, getSession, createRound, createEntry,
  createSet, completeSession, discardSession, getCoverage,
} from '../services/sessions'
import type { TrainingSession, Coverage, EntrySet } from '../services/sessions'

interface SessionState {
  session: TrainingSession | null
  coverage: Coverage | null
  loading: boolean
  busy: boolean
  error: string | null
  start: (dayPlanId: number | null) => Promise<TrainingSession>
  resume: () => Promise<TrainingSession | null>
  refresh: () => Promise<void>
  addRound: () => Promise<number>
  addEntry: (roundId: number, exerciseId: number, position: number) => Promise<void>
  logSet: (entryId: number, s: { set_number: number; weight?: number | null; reps?: number | null; time_seconds?: number | null }) => Promise<EntrySet>
  complete: () => Promise<void>
  discard: () => Promise<void>
}

export const useSessionStore = create<SessionState>((set, get) => ({
  session: null,
  coverage: null,
  loading: false,
  busy: false,
  error: null,

  start: async (dayPlanId) => {
    set({ loading: true, error: null })
    try {
      const session = await createSession(dayPlanId)
      set({ session, loading: false })
      await get().refresh()
      return session
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to start session', loading: false })
      throw e
    }
  },

  resume: async () => {
    const session = await getActiveSession()
    if (!session) {
      set({ session: null, coverage: null })
      return null
    }
    set({ session })
    await get().refresh()
    return session
  },

  refresh: async () => {
    const current = get().session
    if (!current) return
    const [session, coverage] = await Promise.all([
      getSession(current.id),
      getCoverage(current.id),
    ])
    set({ session, coverage })
  },

  addRound: async () => {
    const current = get().session
    if (!current) throw new Error('No active session')
    set({ busy: true })
    try {
      const round = await createRound(current.id)
      await get().refresh()
      return round.id
    } finally {
      set({ busy: false })
    }
  },

  addEntry: async (roundId, exerciseId, position) => {
    set({ busy: true })
    try {
      await createEntry(roundId, exerciseId, position)
      await get().refresh()
    } finally {
      set({ busy: false })
    }
  },

  logSet: async (entryId, s) => {
    set({ busy: true })
    try {
      const logged = await createSet(entryId, s)
      await get().refresh()
      return logged
    } finally {
      set({ busy: false })
    }
  },

  complete: async () => {
    const current = get().session
    if (!current) return
    set({ busy: true })
    try {
      const session = await completeSession(current.id)
      set({ session })
    } finally {
      set({ busy: false })
    }
  },

  discard: async () => {
    const current = get().session
    if (!current) return
    set({ busy: true })
    try {
      await discardSession(current.id)
      set({ session: null, coverage: null })
    } finally {
      set({ busy: false })
    }
  },
}))
