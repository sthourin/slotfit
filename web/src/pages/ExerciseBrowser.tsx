/**
 * Exercise Browser Page
 * Browse and search exercises
 */
import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { exerciseApi, Exercise } from '../services/exercises'
import { equipmentApi, Equipment } from '../services/equipment'
import { createStaple } from '../services/staples'

export default function ExerciseBrowser() {
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedEquipment, setSelectedEquipment] = useState<number[]>([])
  const [equipmentList, setEquipmentList] = useState<Equipment[]>([])
  const [page, setPage] = useState(1)
  // Exercises confirmed to be in the staple pool. A 409 ("already a staple")
  // counts as success: the user's intent is satisfied either way.
  const [stapled, setStapled] = useState<number[]>([])
  const [stapling, setStapling] = useState<number | null>(null)
  const [stapleError, setStapleError] = useState<string | null>(null)
  // Monotonic request counter. Without it a slower earlier fetch (the initial
  // unfiltered load counts every one of the ~3,240 rows) resolves after a
  // newer search and silently overwrites the filtered results.
  const requestSeq = useRef(0)
  const pageSize = 20

  useEffect(() => {
    loadExercises()
    loadEquipment()
  }, [search, selectedEquipment, page])

  const loadExercises = async () => {
    const seq = ++requestSeq.current
    setLoading(true)
    try {
      const params: Parameters<typeof exerciseApi.list>[0] = {
        skip: (page - 1) * pageSize,
        limit: pageSize,
      }
      if (search) params.search = search
      if (selectedEquipment.length > 0) {
        // Use first equipment for now (backend supports single equipment_id)
        params.equipment_id = selectedEquipment[0]
      }
      const response = await exerciseApi.list(params)
      // A newer request has been issued since; its results win.
      if (seq !== requestSeq.current) return
      setExercises(response.exercises)
    } catch (error) {
      if (seq !== requestSeq.current) return
      console.error('Failed to load exercises:', error)
    } finally {
      if (seq === requestSeq.current) setLoading(false)
    }
  }

  const addToStaples = async (exerciseId: number) => {
    setStapleError(null)
    setStapling(exerciseId)
    try {
      await createStaple(exerciseId)
      setStapled((prev) => (prev.includes(exerciseId) ? prev : [...prev, exerciseId]))
    } catch (err) {
      // 409 means it is already in the pool - the desired end state, not a failure.
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setStapled((prev) => (prev.includes(exerciseId) ? prev : [...prev, exerciseId]))
      } else {
        setStapleError(err instanceof Error ? err.message : 'Failed to add to staples')
      }
    } finally {
      setStapling(null)
    }
  }

  const loadEquipment = async () => {
    try {
      const equipment = await equipmentApi.list()
      setEquipmentList(equipment)
    } catch (error) {
      console.error('Failed to load equipment:', error)
    }
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Exercise Browser</h1>

      {stapleError && <div className="text-red-600 mb-4">{stapleError}</div>}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search Exercises
            </label>
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              placeholder="Search by name..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by Equipment
            </label>
            <div className="max-h-32 overflow-y-auto border border-gray-300 rounded-md p-2">
              {equipmentList.map((eq) => (
                <label key={eq.id} className="flex items-center space-x-2 py-1">
                  <input
                    type="checkbox"
                    checked={selectedEquipment.includes(eq.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedEquipment([...selectedEquipment, eq.id])
                      } else {
                        setSelectedEquipment(selectedEquipment.filter((id) => id !== eq.id))
                      }
                      setPage(1)
                    }}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm">{eq.name}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Exercise List */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading exercises...</div>
      ) : exercises.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No exercises found</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {exercises.map((exercise) => (
            <div
              key={exercise.id}
              className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow"
            >
              <h3 className="font-semibold text-lg mb-2">{exercise.name}</h3>
              {exercise.difficulty && (
                <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded mb-2">
                  {exercise.difficulty}
                </span>
              )}
              <div className="text-sm text-gray-600 space-y-1">
                {exercise.primary_equipment && (
                  <div>
                    <strong>Equipment:</strong> {exercise.primary_equipment.name}
                  </div>
                )}
                {exercise.muscle_groups.length > 0 && (
                  <div>
                    <strong>Muscle Groups:</strong>{' '}
                    {exercise.muscle_groups
                      .filter((mg) => mg.level === 1)
                      .map((mg) => mg.name)
                      .join(', ')}
                  </div>
                )}
                {exercise.body_region && (
                  <div>
                    <strong>Region:</strong> {exercise.body_region}
                  </div>
                )}
              </div>
              {exercise.short_demo_url && (
                <a
                  href={exercise.short_demo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-block text-sm text-blue-600 hover:text-blue-800"
                >
                  Watch Demo →
                </a>
              )}
              {/* Accessible name stays "Add to Staples" after a successful add so
                  the control is addressable by the same name throughout. */}
              <div className="mt-3 flex items-center gap-2">
                <button
                  onClick={() => addToStaples(exercise.id)}
                  disabled={stapling !== null}
                  className="text-sm bg-purple-600 text-white px-3 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add to Staples
                </button>
                {stapled.includes(exercise.id) && (
                  <span className="text-sm text-green-700">Added</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      <div className="mt-6 flex justify-center space-x-2">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
          className="px-4 py-2 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
        >
          Previous
        </button>
        <span className="px-4 py-2">Page {page}</span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={exercises.length < pageSize}
          className="px-4 py-2 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
        >
          Next
        </button>
      </div>
    </div>
  )
}
