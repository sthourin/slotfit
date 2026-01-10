/**
 * Personal Records Page
 * Displays all personal records achieved by the user
 */
import { useState, useEffect } from 'react'
import { personalRecordApi, type PersonalRecord, type RecordType } from '../services/personalRecords'
import { exerciseApi, type Exercise } from '../services/exercises'
import PRCard from '../components/records/PRCard'
import PRHistory from '../components/records/PRHistory'

export default function PersonalRecords() {
  const [records, setRecords] = useState<PersonalRecord[]>([])
  const [exerciseDetails, setExerciseDetails] = useState<Map<number, Exercise>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedExerciseId, setSelectedExerciseId] = useState<number | null>(null)
  const [filterType, setFilterType] = useState<'all' | 'weight' | 'reps' | 'volume' | 'time'>('all')

  useEffect(() => {
    loadRecords()
  }, [filterType])

  const loadRecords = async () => {
    setLoading(true)
    setError(null)
    try {
      const params: { record_type?: RecordType } = {}
      if (filterType !== 'all') {
        params.record_type = filterType as RecordType
      }
      const response = await personalRecordApi.list(params)
      setRecords(response.records)

      // Load exercise details
      const exerciseIds = new Set(response.records.map((r) => r.exercise_id))
      const exercises = await Promise.all(
        Array.from(exerciseIds).map((id) => exerciseApi.get(id).catch(() => null))
      )
      const exerciseMap = new Map<number, Exercise>()
      exercises.forEach((ex, idx) => {
        if (ex) {
          exerciseMap.set(Array.from(exerciseIds)[idx], ex)
        }
      })
      setExerciseDetails(exerciseMap)
    } catch (err) {
      console.error('Failed to load personal records:', err)
      setError('Failed to load personal records. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading personal records...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
            <button
              onClick={loadRecords}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Group records by exercise
  const recordsByExercise = new Map<number, PersonalRecord[]>()
  records.forEach((record) => {
    const existing = recordsByExercise.get(record.exercise_id) || []
    recordsByExercise.set(record.exercise_id, [...existing, record])
  })

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Personal Records</h1>
          <p className="text-gray-600">
            Track your best performances across all exercises
          </p>
        </div>

        {/* Filters */}
        <div className="mb-6 flex gap-2">
          <button
            onClick={() => setFilterType('all')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filterType === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilterType('weight')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filterType === 'weight'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            Weight
          </button>
          <button
            onClick={() => setFilterType('reps')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filterType === 'reps'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            Reps
          </button>
          <button
            onClick={() => setFilterType('volume')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filterType === 'volume'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            Volume
          </button>
          <button
            onClick={() => setFilterType('time')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filterType === 'time'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            Time
          </button>
        </div>

        {records.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <p className="text-gray-500 text-lg">No personal records yet.</p>
            <p className="text-gray-400 mt-2">Complete workouts to start tracking your PRs!</p>
          </div>
        ) : (
          <div className="space-y-4">
            {Array.from(recordsByExercise.entries()).map(([exerciseId, exerciseRecords]) => {
              const exercise = exerciseDetails.get(exerciseId)
              const latestPR = exerciseRecords.sort(
                (a, b) => new Date(b.achieved_at).getTime() - new Date(a.achieved_at).getTime()
              )[0]

              return (
                <div key={exerciseId}>
                  <PRCard
                    exercise={exercise}
                    exerciseId={exerciseId}
                    latestPR={latestPR}
                    allRecords={exerciseRecords}
                    onClick={() => setSelectedExerciseId(selectedExerciseId === exerciseId ? null : exerciseId)}
                  />
                  {selectedExerciseId === exerciseId && (
                    <div className="mt-2 ml-4">
                      <PRHistory records={exerciseRecords} exercise={exercise} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
