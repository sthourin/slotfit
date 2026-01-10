/**
 * Analytics Dashboard Page
 * Shows workout analytics and insights
 */
import { useState, useEffect } from 'react'
import { analyticsApi, type WeeklyVolumeResponse, type SlotPerformanceResponse } from '../services/analytics'
import { routineApi, type RoutineTemplate } from '../services/routines'
import VolumeChart from '../components/analytics/VolumeChart'
import ProgressionChart from '../components/analytics/ProgressionChart'
import MovementBalance from '../components/analytics/MovementBalance'
import SlotPerformance from '../components/analytics/SlotPerformance'

export default function Analytics() {
  const [weeklyVolume, setWeeklyVolume] = useState<WeeklyVolumeResponse | null>(null)
  const [routines, setRoutines] = useState<RoutineTemplate[]>([])
  const [selectedRoutineId, setSelectedRoutineId] = useState<number | null>(null)
  const [slotPerformance, setSlotPerformance] = useState<SlotPerformanceResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (selectedRoutineId) {
      loadSlotPerformance(selectedRoutineId)
    }
  }, [selectedRoutineId])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      // Load weekly volume
      const volume = await analyticsApi.getWeeklyVolume()
      setWeeklyVolume(volume)

      // Load routines for slot performance
      const routinesResponse = await routineApi.list()
      setRoutines(routinesResponse.routines)
      if (routinesResponse.routines.length > 0) {
        setSelectedRoutineId(routinesResponse.routines[0].id)
      }
    } catch (err) {
      console.error('Failed to load analytics:', err)
      setError('Failed to load analytics data. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const loadSlotPerformance = async (routineId: number) => {
    try {
      const performance = await analyticsApi.getSlotPerformance(routineId)
      setSlotPerformance(performance)
    } catch (err) {
      console.error('Failed to load slot performance:', err)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading analytics...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="container mx-auto px-4 max-w-6xl">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
            <button
              onClick={loadData}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Analytics Dashboard</h1>
          <p className="text-gray-600">
            Track your progress and analyze your workout patterns
          </p>
        </div>

        <div className="space-y-6">
          {/* Weekly Volume Chart */}
          {weeklyVolume && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold mb-4">Weekly Volume</h2>
              <VolumeChart data={weeklyVolume} />
            </div>
          )}

          {/* Movement Balance */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold mb-4">Movement Balance</h2>
            <MovementBalance />
          </div>

          {/* Slot Performance */}
          {routines.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">Slot Performance</h2>
                <select
                  value={selectedRoutineId || ''}
                  onChange={(e) => setSelectedRoutineId(Number(e.target.value))}
                  className="px-4 py-2 border rounded-lg"
                >
                  {routines.map((routine) => (
                    <option key={routine.id} value={routine.id}>
                      {routine.name}
                    </option>
                  ))}
                </select>
              </div>
              {slotPerformance && <SlotPerformance data={slotPerformance} />}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
