/**
 * TestServices.tsx - API & Store Smoke Test Page
 * 
 * TEMPORARY: Remove this file and its route after testing Phase 3
 * 
 * Tests all API services and Zustand stores to verify Phase 3 is working
 */
import { useState, useEffect } from 'react'
import {
  exerciseApi,
  routineApi,
  workoutApi,
  equipmentProfileApi,
  slotTemplateApi,
  recommendationApi,
  analyticsApi,
  muscleGroupApi,
  equipmentApi,
  personalRecordApi,
} from '../services'
import { useWorkoutStore } from '../stores/workoutStore'
import { useEquipmentStore } from '../stores/equipmentStore'

type TestStatus = 'pending' | 'loading' | 'success' | 'error'

interface TestResult {
  name: string
  status: TestStatus
  data?: any
  error?: string
  count?: number
}

export default function TestServices() {
  const [results, setResults] = useState<TestResult[]>([])
  const [isRunning, setIsRunning] = useState(false)
  
  // Zustand stores
  const workoutStore = useWorkoutStore()
  const equipmentStore = useEquipmentStore()

  const updateResult = (name: string, update: Partial<TestResult>) => {
    setResults(prev => 
      prev.map(r => r.name === name ? { ...r, ...update } : r)
    )
  }

  const runAllTests = async () => {
    setIsRunning(true)
    
    // Initialize all tests as pending
    const initialResults: TestResult[] = [
      { name: 'Exercises API', status: 'pending' },
      { name: 'Muscle Groups API', status: 'pending' },
      { name: 'Equipment API', status: 'pending' },
      { name: 'Equipment Profiles API', status: 'pending' },
      { name: 'Routines API', status: 'pending' },
      { name: 'Slot Templates API', status: 'pending' },
      { name: 'Workouts API', status: 'pending' },
      { name: 'Personal Records API', status: 'pending' },
      { name: 'Analytics - Weekly Volume', status: 'pending' },
      { name: 'Recommendations API', status: 'pending' },
      { name: 'Equipment Store (Zustand)', status: 'pending' },
      { name: 'Workout Store (Zustand)', status: 'pending' },
    ]
    setResults(initialResults)

    // Run tests sequentially for clarity
    
    // 1. Exercises
    updateResult('Exercises API', { status: 'loading' })
    try {
      const exercises = await exerciseApi.list({ limit: 5 })
      updateResult('Exercises API', { 
        status: 'success', 
        count: exercises.total,
        data: exercises.exercises.slice(0, 3).map(e => e.name)
      })
    } catch (err: any) {
      updateResult('Exercises API', { status: 'error', error: err.message })
    }

    // 2. Muscle Groups
    updateResult('Muscle Groups API', { status: 'loading' })
    try {
      const muscleGroups = await muscleGroupApi.list()
      updateResult('Muscle Groups API', { 
        status: 'success', 
        count: muscleGroups.length,
        data: muscleGroups.slice(0, 5).map(mg => mg.name)
      })
    } catch (err: any) {
      updateResult('Muscle Groups API', { status: 'error', error: err.message })
    }

    // 3. Equipment
    updateResult('Equipment API', { status: 'loading' })
    try {
      const equipment = await equipmentApi.list()
      updateResult('Equipment API', { 
        status: 'success', 
        count: equipment.length,
        data: equipment.slice(0, 5).map(e => e.name)
      })
    } catch (err: any) {
      updateResult('Equipment API', { status: 'error', error: err.message })
    }

    // 4. Equipment Profiles
    updateResult('Equipment Profiles API', { status: 'loading' })
    try {
      const profiles = await equipmentProfileApi.list()
      updateResult('Equipment Profiles API', { 
        status: 'success', 
        count: profiles.length,
        data: profiles.map(p => `${p.name}${p.is_default ? ' (default)' : ''}`)
      })
    } catch (err: any) {
      updateResult('Equipment Profiles API', { status: 'error', error: err.message })
    }

    // 5. Routines
    updateResult('Routines API', { status: 'loading' })
    try {
      const response = await routineApi.list()
      updateResult('Routines API', { 
        status: 'success', 
        count: response.total,
        data: response.routines.slice(0, 3).map(r => r.name)
      })
    } catch (err: any) {
      updateResult('Routines API', { status: 'error', error: err.message })
    }

    // 6. Slot Templates
    updateResult('Slot Templates API', { status: 'loading' })
    try {
      const templates = await slotTemplateApi.list()
      updateResult('Slot Templates API', { 
        status: 'success', 
        count: templates.length,
        data: templates.slice(0, 3).map(t => `${t.name} (${t.slot_type})`)
      })
    } catch (err: any) {
      updateResult('Slot Templates API', { status: 'error', error: err.message })
    }

    // 7. Workouts
    updateResult('Workouts API', { status: 'loading' })
    try {
      const workouts = await workoutApi.list({ limit: 5 })
      updateResult('Workouts API', { 
        status: 'success', 
        count: workouts.total,
        data: workouts.workouts.slice(0, 3).map(w => `${w.state} - ${w.started_at || 'not started'}`)
      })
    } catch (err: any) {
      updateResult('Workouts API', { status: 'error', error: err.message })
    }

    // 8. Personal Records
    updateResult('Personal Records API', { status: 'loading' })
    try {
      const response = await personalRecordApi.list()
      updateResult('Personal Records API', { 
        status: 'success', 
        count: response.total,
        data: response.records.slice(0, 3).map(r => `${r.record_type}: ${r.value}`)
      })
    } catch (err: any) {
      updateResult('Personal Records API', { status: 'error', error: err.message })
    }

    // 9. Analytics - Weekly Volume
    updateResult('Analytics - Weekly Volume', { status: 'loading' })
    try {
      const response = await analyticsApi.getWeeklyVolume()
      updateResult('Analytics - Weekly Volume', { 
        status: 'success', 
        count: response.muscle_groups.length,
        data: response.muscle_groups.slice(0, 3).map(v => `${v.name}: ${v.total_sets} sets`)
      })
    } catch (err: any) {
      updateResult('Analytics - Weekly Volume', { status: 'error', error: err.message })
    }

    // 10. Recommendations (requires muscle group and equipment IDs)
    updateResult('Recommendations API', { status: 'loading' })
    try {
      // Try to get recommendations for a common muscle group (biceps = usually id 1-10 range)
      // and with bodyweight (usually id 1)
      const recs = await recommendationApi.getRecommendations({
        muscle_group_ids: [1],
        available_equipment_ids: [1],
        limit: 3
      })
      updateResult('Recommendations API', { 
        status: 'success', 
        count: recs.recommendations.length,
        data: recs.recommendations.map(r => `${r.exercise_name} (${(r.priority_score * 100).toFixed(0)}%)`)
      })
    } catch (err: any) {
      updateResult('Recommendations API', { status: 'error', error: err.message })
    }

    // 11. Equipment Store
    updateResult('Equipment Store (Zustand)', { status: 'loading' })
    try {
      await equipmentStore.loadProfiles()
      const profiles = equipmentStore.profiles
      updateResult('Equipment Store (Zustand)', { 
        status: 'success', 
        count: profiles.length,
        data: `Loaded ${profiles.length} profiles, default: ${equipmentStore.defaultProfileId}`
      })
    } catch (err: any) {
      updateResult('Equipment Store (Zustand)', { status: 'error', error: err.message })
    }

    // 12. Workout Store (just check it initializes)
    updateResult('Workout Store (Zustand)', { status: 'loading' })
    try {
      // Just verify the store is accessible and has expected shape
      const hasExpectedShape = 
        'activeWorkout' in workoutStore &&
        'activeSlots' in workoutStore &&
        'initializeWorkout' in workoutStore
      
      if (hasExpectedShape) {
        updateResult('Workout Store (Zustand)', { 
          status: 'success', 
          data: `Store OK. Active workout: ${workoutStore.activeWorkout?.id || 'none'}`
        })
      } else {
        throw new Error('Store missing expected properties')
      }
    } catch (err: any) {
      updateResult('Workout Store (Zustand)', { status: 'error', error: err.message })
    }

    setIsRunning(false)
  }

  // Auto-run on mount
  useEffect(() => {
    runAllTests()
  }, [])

  const getStatusColor = (status: TestStatus) => {
    switch (status) {
      case 'success': return 'bg-green-100 text-green-800 border-green-200'
      case 'error': return 'bg-red-100 text-red-800 border-red-200'
      case 'loading': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      default: return 'bg-gray-100 text-gray-600 border-gray-200'
    }
  }

  const getStatusIcon = (status: TestStatus) => {
    switch (status) {
      case 'success': return '✓'
      case 'error': return '✗'
      case 'loading': return '⟳'
      default: return '○'
    }
  }

  const successCount = results.filter(r => r.status === 'success').length
  const errorCount = results.filter(r => r.status === 'error').length

  return (
    <div className="container mx-auto px-6 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Phase 3 Test Suite</h1>
        <p className="text-gray-600">
          API Services & Zustand Stores Smoke Test
        </p>
        <p className="text-sm text-amber-600 mt-2">
          ⚠️ Remove this page after testing is complete
        </p>
      </div>

      {/* Summary */}
      <div className="mb-6 flex gap-4">
        <div className="bg-white rounded-lg shadow px-4 py-3 flex items-center gap-2">
          <span className="text-2xl font-bold text-green-600">{successCount}</span>
          <span className="text-gray-600">Passed</span>
        </div>
        <div className="bg-white rounded-lg shadow px-4 py-3 flex items-center gap-2">
          <span className="text-2xl font-bold text-red-600">{errorCount}</span>
          <span className="text-gray-600">Failed</span>
        </div>
        <button
          onClick={runAllTests}
          disabled={isRunning}
          className="ml-auto bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRunning ? 'Running...' : 'Re-run Tests'}
        </button>
      </div>

      {/* Results */}
      <div className="space-y-3">
        {results.map((result) => (
          <div
            key={result.name}
            className={`rounded-lg border p-4 ${getStatusColor(result.status)}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xl font-mono">{getStatusIcon(result.status)}</span>
                <div>
                  <h3 className="font-semibold">{result.name}</h3>
                  {result.count !== undefined && (
                    <p className="text-sm opacity-75">
                      {result.count} {result.count === 1 ? 'item' : 'items'} found
                    </p>
                  )}
                </div>
              </div>
            </div>
            
            {result.error && (
              <div className="mt-2 text-sm bg-red-50 rounded p-2 font-mono">
                {result.error}
              </div>
            )}
            
            {result.data && !result.error && (
              <div className="mt-2 text-sm bg-white/50 rounded p-2">
                {Array.isArray(result.data) ? (
                  <ul className="list-disc list-inside">
                    {result.data.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <span>{result.data}</span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Instructions */}
      <div className="mt-8 bg-blue-50 rounded-lg p-4 border border-blue-200">
        <h3 className="font-semibold text-blue-800 mb-2">Next Steps</h3>
        <ul className="text-blue-700 text-sm space-y-1">
          <li>• If all tests pass, you're ready for Phase 4 (Web Workout Execution)</li>
          <li>• If Recommendations API fails with no results, check the backend filtering logic</li>
          <li>• If any API fails with "Network Error", ensure backend is running on port 8000</li>
          <li>• Remove this test page once you've verified everything works</li>
        </ul>
      </div>
    </div>
  )
}
