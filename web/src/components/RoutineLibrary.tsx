/**
 * Routine Library Component
 * Lists routines and allows edit/copy/delete actions
 */
import { useEffect, useMemo, useState } from 'react'
import { routineApi, type RoutineTemplate } from '../services/routines'
import { useRoutineStore } from '../stores/routineStore'
import { TagDisplay } from './TagDisplay'

export default function RoutineLibrary() {
  const { currentRoutine, setCurrentRoutine, loadRoutine } = useRoutineStore()
  const [routines, setRoutines] = useState<RoutineTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busyIds, setBusyIds] = useState<Set<number>>(new Set())

  const currentRoutineId = currentRoutine?.id ?? null

  const isBusy = useMemo(() => {
    return (id: number) => busyIds.has(id)
  }, [busyIds])

  const updateBusy = (id: number, busy: boolean) => {
    setBusyIds((prev) => {
      const next = new Set(prev)
      if (busy) {
        next.add(id)
      } else {
        next.delete(id)
      }
      return next
    })
  }

  const loadRoutines = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await routineApi.list()
      setRoutines(response.routines)
    } catch (err) {
      console.error('Failed to load routines:', err)
      setError('Failed to load routines. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRoutines()
  }, [])

  useEffect(() => {
    if (currentRoutineId) {
      loadRoutines()
    }
  }, [currentRoutineId])

  const handleNewRoutine = () => {
    setCurrentRoutine({
      name: 'New Routine',
      routineType: 'custom',
      workoutStyle: 'custom',
      description: '',
      tags: [],
      slots: [],
    })
  }

  const handleEdit = async (routineId: number) => {
    updateBusy(routineId, true)
    try {
      await loadRoutine(routineId)
    } catch (err) {
      console.error('Failed to load routine:', err)
      alert('Failed to load routine. Please try again.')
    } finally {
      updateBusy(routineId, false)
    }
  }

  const handleCopy = async (routineId: number) => {
    updateBusy(routineId, true)
    try {
      const routine = await routineApi.get(routineId)
      const created = await routineApi.create({
        name: `Copy of ${routine.name}`,
        routine_type: routine.routine_type,
        workout_style: routine.workout_style,
        description: routine.description,
        slots: routine.slots.map((slot) => ({
          name: slot.name || null,
          order: slot.order,
          muscle_group_ids: slot.muscle_group_ids || [],
          superset_tag: slot.superset_tag || null,
          selected_exercise_id: slot.selected_exercise_id || null,
          workout_style: slot.workout_style || null,
          slot_type: slot.slot_type,
          slot_template_id: slot.slot_template_id || null,
          time_limit_seconds: slot.time_limit_seconds || null,
          required_equipment_ids: slot.required_equipment_ids || null,
          target_reps_min: slot.target_reps_min || null,
          target_reps_max: slot.target_reps_max || null,
          progression_rule: slot.progression_rule || null,
        })),
      })

      if (routine.tags && routine.tags.length > 0) {
        for (const tag of routine.tags) {
          await routineApi.addTag(created.id, tag.name)
        }
      }

      await loadRoutine(created.id)
      await loadRoutines()
    } catch (err) {
      console.error('Failed to copy routine:', err)
      alert('Failed to copy routine. Please try again.')
    } finally {
      updateBusy(routineId, false)
    }
  }

  const handleDelete = async (routineId: number) => {
    if (!confirm('Delete this routine? This cannot be undone.')) return
    updateBusy(routineId, true)
    try {
      await routineApi.delete(routineId)
      if (currentRoutineId === routineId) {
        setCurrentRoutine(null)
      }
      await loadRoutines()
    } catch (err) {
      console.error('Failed to delete routine:', err)
      alert('Failed to delete routine. Please try again.')
    } finally {
      updateBusy(routineId, false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Routine Library</h2>
        <button
          onClick={handleNewRoutine}
          className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          New Routine
        </button>
      </div>

      {loading && routines.length === 0 ? (
        <div className="text-sm text-gray-500">Loading routines...</div>
      ) : error ? (
        <div className="text-sm text-red-600">{error}</div>
      ) : routines.length === 0 ? (
        <div className="text-sm text-gray-500">
          No routines yet. Create a new routine to get started.
        </div>
      ) : (
        <div className="space-y-2">
          {routines.map((routine) => {
            const selected = routine.id === currentRoutineId
            return (
              <div
                key={routine.id}
                className={`border rounded-md p-3 ${
                  selected ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="font-semibold">{routine.name}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {routine.slots.length} slot{routine.slots.length !== 1 ? 's' : ''}
                    </div>
                    {routine.tags && routine.tags.length > 0 && (
                      <div className="mt-2">
                        <TagDisplay tags={routine.tags} size="sm" />
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleEdit(routine.id)}
                      disabled={isBusy(routine.id)}
                      className="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleCopy(routine.id)}
                      disabled={isBusy(routine.id)}
                      className="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
                    >
                      Copy
                    </button>
                    <button
                      onClick={() => handleDelete(routine.id)}
                      disabled={isBusy(routine.id)}
                      className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
