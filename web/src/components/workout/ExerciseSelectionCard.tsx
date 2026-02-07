/**
 * ExerciseSelectionCard - Displays the currently selected exercise with "why it fits" explanation
 * Frames the exercise as one option that fills the slot spec, not the primary focus
 */
import { useState } from 'react'
import type { Exercise } from '../../services/exercises'
import MatchExplanation from './MatchExplanation'

interface MuscleGroup {
  id: number
  name: string
}

interface ExerciseSelectionCardProps {
  exercise: Exercise | null
  loading: boolean
  primaryMuscleGroup: MuscleGroup | null
  secondaryMuscleGroups: MuscleGroup[]
  lastPerformed?: string | null
  slotState: 'not_started' | 'in_progress' | 'completed' | 'skipped'
  onSwap: () => void
  onStart: () => void
  onComplete: () => void
  onSelectExercise: () => void
}

export default function ExerciseSelectionCard({
  exercise,
  loading,
  primaryMuscleGroup,
  secondaryMuscleGroups,
  lastPerformed,
  slotState,
  onSwap,
  onStart,
  onComplete,
  onSelectExercise,
}: ExerciseSelectionCardProps) {
  const [showDetails, setShowDetails] = useState(true)

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/2 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
        </div>
      </div>
    )
  }

  if (!exercise) {
    // No exercise selected yet
    return (
      <div className="bg-white rounded-lg border border-gray-200 border-dashed p-6 text-center">
        <div className="text-gray-500 mb-4">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M12 6v6m0 0v6m0-6h6m-6 0H6"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Exercise Selected</h3>
        <p className="text-sm text-gray-500 mb-4">
          Choose an exercise that matches this slot's specifications
        </p>
        <button
          onClick={onSelectExercise}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Select Exercise
        </button>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          Current Exercise
        </h3>
        {slotState !== 'completed' && slotState !== 'skipped' && (
          <button
            onClick={onSwap}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            Swap Exercise
          </button>
        )}
      </div>

      {/* Exercise Info */}
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h4 className="text-xl font-semibold text-gray-900">{exercise.name}</h4>
            {exercise.difficulty && (
              <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">
                {exercise.difficulty}
              </span>
            )}
          </div>
        </div>

        {/* Match Explanation - Collapsible */}
        <div className="mb-4">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            <span>{showDetails ? 'Hide' : 'Show'} why this fits</span>
            <svg
              className={`w-4 h-4 transition-transform ${showDetails ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showDetails && (
            <div className="mt-2">
              <MatchExplanation
                exercise={exercise}
                primaryMuscleGroup={primaryMuscleGroup}
                secondaryMuscleGroups={secondaryMuscleGroups}
                lastPerformed={lastPerformed}
              />
            </div>
          )}
        </div>

        {/* Video/Guide Links */}
        <div className="flex gap-2 mb-4">
          {exercise.short_demo_url && (
            <a
              href={exercise.short_demo_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-3 py-1.5 text-sm bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors"
            >
              <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              Watch Demo
            </a>
          )}
          {exercise.in_depth_url && (
            <a
              href={exercise.in_depth_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-3 py-1.5 text-sm bg-gray-50 text-gray-700 rounded-md hover:bg-gray-100 transition-colors"
            >
              <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
              Form Guide
            </a>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          {slotState === 'not_started' && (
            <button
              onClick={onStart}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Start Slot
            </button>
          )}
          {slotState === 'in_progress' && (
            <button
              onClick={onComplete}
              className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              Complete Slot
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
