/**
 * Exercise Panel Component
 * Displays exercise details with video links
 */
import { type Exercise } from '../../services/exercises'

interface ExercisePanelProps {
  exercise: Exercise
}

export default function ExercisePanel({ exercise }: ExercisePanelProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h3 className="text-xl font-semibold mb-4">Exercise Details</h3>

      {/* Description */}
      {exercise.description && (
        <div className="mb-4">
          <p className="text-gray-700">{exercise.description}</p>
        </div>
      )}

      {/* Video Links */}
      <div className="mb-4 space-y-2">
        {exercise.short_demo_url && (
          <a
            href={exercise.short_demo_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
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
            Watch Demo Video
          </a>
        )}

        {exercise.in_depth_url && (
          <a
            href={exercise.in_depth_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
            In-Depth Guide
          </a>
        )}
      </div>

      {/* Exercise Metadata */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        {exercise.primary_equipment && (
          <div>
            <span className="font-medium text-gray-700">Equipment:</span>
            <span className="ml-2 text-gray-600">{exercise.primary_equipment.name}</span>
          </div>
        )}

        {exercise.muscle_groups.length > 0 && (
          <div>
            <span className="font-medium text-gray-700">Muscle Groups:</span>
            <span className="ml-2 text-gray-600">
              {exercise.muscle_groups
                .filter((mg) => mg.level === 1)
                .map((mg) => mg.name)
                .join(', ')}
            </span>
          </div>
        )}

        {exercise.mechanics && (
          <div>
            <span className="font-medium text-gray-700">Mechanics:</span>
            <span className="ml-2 text-gray-600">{exercise.mechanics}</span>
          </div>
        )}

        {exercise.force_type && (
          <div>
            <span className="font-medium text-gray-700">Force Type:</span>
            <span className="ml-2 text-gray-600">{exercise.force_type}</span>
          </div>
        )}
      </div>

      {/* Default Parameters (if variant) */}
      {(exercise.default_sets ||
        exercise.default_reps ||
        exercise.default_weight ||
        exercise.default_rest_seconds) && (
        <div className="mt-4 pt-4 border-t">
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Default Parameters
          </h4>
          <div className="flex flex-wrap gap-2 text-sm">
            {exercise.default_sets && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                {exercise.default_sets} sets
              </span>
            )}
            {exercise.default_reps && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                {exercise.default_reps} reps
              </span>
            )}
            {exercise.default_weight && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                {exercise.default_weight} lbs
              </span>
            )}
            {exercise.default_rest_seconds && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                {Math.floor(exercise.default_rest_seconds / 60)} min rest
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
