/**
 * Workout Controls Component
 * Pause/Resume/Complete/Abandon buttons
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { type WorkoutState } from '../../services/workouts'

interface WorkoutControlsProps {
  workoutState: WorkoutState
  onPause: () => Promise<void>
  onResume: () => Promise<void>
  onComplete: () => Promise<void>
  onAbandon: () => Promise<void>
}

export default function WorkoutControls({
  workoutState,
  onPause,
  onResume,
  onComplete,
  onAbandon,
}: WorkoutControlsProps) {
  const navigate = useNavigate()
  const [processing, setProcessing] = useState(false)

  const handleComplete = async () => {
    if (
      !window.confirm(
        'Are you sure you want to complete this workout? This will save all your progress.'
      )
    ) {
      return
    }

    setProcessing(true)
    try {
      await onComplete()
      // Summary will be shown by the Workout page component
    } catch (error) {
      console.error('Failed to complete workout:', error)
      alert('Failed to complete workout. Please try again.')
    } finally {
      setProcessing(false)
    }
  }

  const handleAbandon = async () => {
    if (
      !window.confirm(
        'Are you sure you want to abandon this workout? All unsaved progress will be lost.'
      )
    ) {
      return
    }

    setProcessing(true)
    try {
      await onAbandon()
      navigate('/workout/start')
    } catch (error) {
      console.error('Failed to abandon workout:', error)
      alert('Failed to abandon workout. Please try again.')
    } finally {
      setProcessing(false)
    }
  }

  const handlePause = async () => {
    setProcessing(true)
    try {
      await onPause()
    } catch (error) {
      console.error('Failed to pause workout:', error)
      alert('Failed to pause workout. Please try again.')
    } finally {
      setProcessing(false)
    }
  }

  const handleResume = async () => {
    setProcessing(true)
    try {
      await onResume()
    } catch (error) {
      console.error('Failed to resume workout:', error)
      alert('Failed to resume workout. Please try again.')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h3 className="text-xl font-semibold mb-4">Workout Controls</h3>

      <div className="space-y-3">
        {/* Pause/Resume */}
        {workoutState === 'active' && (
          <button
            onClick={handlePause}
            disabled={processing}
            className="w-full px-4 py-3 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {processing ? 'Pausing...' : 'Pause Workout'}
          </button>
        )}

        {workoutState === 'paused' && (
          <button
            onClick={handleResume}
            disabled={processing}
            className="w-full px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {processing ? 'Resuming...' : 'Resume Workout'}
          </button>
        )}

        {/* Complete */}
        {(workoutState === 'active' || workoutState === 'paused') && (
          <button
            onClick={handleComplete}
            disabled={processing}
            className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {processing ? 'Completing...' : 'Complete Workout'}
          </button>
        )}

        {/* Abandon */}
        {(workoutState === 'active' || workoutState === 'paused' || workoutState === 'draft') && (
          <button
            onClick={handleAbandon}
            disabled={processing}
            className="w-full px-4 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {processing ? 'Abandoning...' : 'Abandon Workout'}
          </button>
        )}
      </div>

      {/* Status Info */}
      <div className="mt-4 pt-4 border-t">
        <div className="text-sm text-gray-600">
          <div className="flex items-center justify-between">
            <span>Status:</span>
            <span className="font-medium capitalize">{workoutState}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
