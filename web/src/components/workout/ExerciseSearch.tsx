/**
 * Exercise Search Component
 * Search and filter all exercises
 */
import { useState, useEffect } from 'react'
import { exerciseApi, type Exercise } from '../../services/exercises'

interface ExerciseSearchProps {
  searchQuery: string
  searchResults: Exercise[]
  onSearch: (query: string) => void
  onSelectExercise: (exerciseId: number, exerciseName: string) => void
}

export default function ExerciseSearch({
  searchQuery,
  searchResults,
  onSearch,
  onSelectExercise,
}: ExerciseSearchProps) {
  const [localQuery, setLocalQuery] = useState(searchQuery)
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    // Debounce search
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }

    const timer = setTimeout(() => {
      onSearch(localQuery)
    }, 300)

    setDebounceTimer(timer)

    return () => {
      if (debounceTimer) {
        clearTimeout(debounceTimer)
      }
    }
  }, [localQuery])

  return (
    <div className="space-y-4">
      <div>
        <input
          type="text"
          value={localQuery}
          onChange={(e) => setLocalQuery(e.target.value)}
          placeholder="Search exercises by name..."
          className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {searchResults.length === 0 && localQuery && (
        <div className="text-center py-8 text-gray-500">
          <p>No exercises found matching "{localQuery}"</p>
        </div>
      )}

      {searchResults.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm text-gray-600">
            Found {searchResults.length} exercise{searchResults.length !== 1 ? 's' : ''}
          </div>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {searchResults.map((exercise) => (
              <div
                key={exercise.id}
                className="border rounded-lg p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                onClick={() => onSelectExercise(exercise.id, exercise.name)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-semibold">{exercise.name}</h4>
                    {exercise.description && (
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                        {exercise.description}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2 mt-2">
                      {exercise.difficulty && (
                        <span className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                          {exercise.difficulty}
                        </span>
                      )}
                      {exercise.primary_equipment && (
                        <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                          {exercise.primary_equipment.name}
                        </span>
                      )}
                      {exercise.mechanics && (
                        <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                          {exercise.mechanics}
                        </span>
                      )}
                      {exercise.force_type && (
                        <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                          {exercise.force_type}
                        </span>
                      )}
                    </div>
                    {(exercise.short_demo_url || exercise.in_depth_url) && (
                      <div className="flex gap-2 mt-2">
                        {exercise.short_demo_url && (
                          <a
                            href={exercise.short_demo_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-sm text-blue-600 hover:text-blue-800 underline"
                          >
                            Watch Demo
                          </a>
                        )}
                        {exercise.in_depth_url && (
                          <a
                            href={exercise.in_depth_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-sm text-blue-600 hover:text-blue-800 underline"
                          >
                            Learn More
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onSelectExercise(exercise.id, exercise.name)
                    }}
                    className="ml-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Select
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
