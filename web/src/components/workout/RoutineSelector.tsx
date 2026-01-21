/**
 * Routine Selector Component
 * Displays a list of routines for selection
 */
import { useState, useEffect } from 'react'
import { routineApi, type RoutineTemplateListResponse } from '../../services/routines'
import { TagDisplay } from '../TagDisplay'

interface RoutineSelectorProps {
  selectedRoutineId: number | null
  onSelectRoutine: (routineId: number) => void
  loading?: boolean
}

export default function RoutineSelector({
  selectedRoutineId,
  onSelectRoutine,
  loading: externalLoading,
}: RoutineSelectorProps) {
  const [routines, setRoutines] = useState<RoutineTemplateListResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRoutines()
  }, [])

  const loadRoutines = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await routineApi.list()
      setRoutines(data)
    } catch (err) {
      console.error('Failed to load routines:', err)
      setError('Failed to load routines. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const isLoading = loading || externalLoading

  if (isLoading && !routines) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Loading routines...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={loadRoutines}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!routines || routines.routines.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600 mb-4">No routines found.</p>
        <p className="text-sm text-gray-500">
          Create a routine in the{' '}
          <a href="/" className="text-blue-600 hover:underline">
            Routine Designer
          </a>
          .
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {routines.routines.map((routine) => (
        <button
          key={routine.id}
          onClick={() => onSelectRoutine(routine.id)}
          className={`w-full text-left p-4 border-2 rounded-lg transition-colors ${
            selectedRoutineId === routine.id
              ? 'border-blue-600 bg-blue-50'
              : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="font-semibold text-lg">{routine.name}</div>
              {routine.description && (
                <div className="text-sm text-gray-600 mt-1">{routine.description}</div>
              )}
              <div className="flex gap-2 mt-2">
                {routine.routine_type && (
                  <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                    {routine.routine_type}
                  </span>
                )}
                {routine.workout_style && (
                  <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                    {routine.workout_style}
                  </span>
                )}
                <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                  {routine.slots.length} slot{routine.slots.length !== 1 ? 's' : ''}
                </span>
              </div>
              {routine.tags && routine.tags.length > 0 && (
                <div className="mt-2">
                  <TagDisplay tags={routine.tags} size="sm" />
                </div>
              )}
            </div>
            {selectedRoutineId === routine.id && (
              <div className="ml-4 text-blue-600">
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            )}
          </div>
        </button>
      ))}
    </div>
  )
}
