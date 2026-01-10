/**
 * Routine Header Component
 * Displays and edits routine metadata
 */
import { useState } from 'react'
import { useRoutineStore } from '../stores/routineStore'

export default function RoutineHeader() {
  const { currentRoutine, setCurrentRoutine, saveRoutine, saving } = useRoutineStore()
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  if (!currentRoutine) return null

  const updateField = <K extends keyof typeof currentRoutine>(
    field: K, 
    value: typeof currentRoutine[K]
  ) => {
    setCurrentRoutine({
      ...currentRoutine,
      [field]: value,
    })
  }

  const handleSave = async () => {
    try {
      setSaveMessage(null)
      await saveRoutine()
      setSaveMessage('Routine saved successfully!')
      setTimeout(() => setSaveMessage(null), 3000)
    } catch (error: any) {
      const errorMsg = error?.message || 'Failed to save routine'
      setSaveMessage(errorMsg)
      console.error('Save error:', error)
      setTimeout(() => setSaveMessage(null), 5000)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h2 className="text-xl font-semibold mb-4">Routine Details</h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Routine Name
          </label>
          <input
            type="text"
            value={currentRoutine.name}
            onChange={(e) => updateField('name', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter routine name"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Routine Type
            </label>
            <select
              value={currentRoutine.routineType}
              onChange={(e) => updateField('routineType', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="anterior">Anterior</option>
              <option value="posterior">Posterior</option>
              <option value="full_body">Full Body</option>
              <option value="custom">Custom</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Workout Style
            </label>
            <select
              value={currentRoutine.workoutStyle}
              onChange={(e) => updateField('workoutStyle', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="5x5">5x5</option>
              <option value="HIIT">HIIT</option>
              <option value="volume">Volume</option>
              <option value="strength">Strength</option>
              <option value="custom">Custom</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            value={currentRoutine.description}
            onChange={(e) => updateField('description', e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Optional description"
          />
        </div>

        {/* Save Button */}
        <div className="pt-4 border-t">
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : currentRoutine.id ? 'Save Changes' : 'Save Routine'}
          </button>
          {saveMessage && (
            <p className={`mt-2 text-sm text-center ${
              saveMessage.includes('Failed') || saveMessage.includes('Error') || saveMessage.includes('error') ? 'text-red-600' : 'text-green-600'
            }`}>
              {saveMessage}
            </p>
          )}
          {currentRoutine.id && (
            <p className="mt-2 text-xs text-gray-500 text-center">
              Routine ID: {currentRoutine.id}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
