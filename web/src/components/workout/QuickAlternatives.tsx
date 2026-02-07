/**
 * QuickAlternatives - Inline strip showing alternative exercises that match the slot spec
 * Allows quick swapping without opening the full exercise selector
 */

interface Alternative {
  exerciseId: number
  exerciseName: string
  matchScore?: number // 0-100 percentage
}

interface QuickAlternativesProps {
  currentExerciseId: number | null
  alternatives: Alternative[]
  loading: boolean
  onSelect: (exerciseId: number, exerciseName: string) => void
  onShowMore: () => void
  disabled?: boolean
}

export default function QuickAlternatives({
  currentExerciseId,
  alternatives,
  loading,
  onSelect,
  onShowMore,
  disabled = false,
}: QuickAlternativesProps) {
  // Filter out the current exercise and limit to 3-4 alternatives
  const filteredAlternatives = alternatives
    .filter((alt) => alt.exerciseId !== currentExerciseId)
    .slice(0, 3)

  const remainingCount = Math.max(0, alternatives.length - filteredAlternatives.length - 1)

  if (loading) {
    return (
      <div className="bg-gray-50 rounded-lg p-3">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          Loading Alternatives...
        </div>
        <div className="flex gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse h-8 w-24 bg-gray-200 rounded-md"></div>
          ))}
        </div>
      </div>
    )
  }

  if (filteredAlternatives.length === 0 && !loading) {
    return null // Don't show section if no alternatives
  }

  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
        Quick Alternatives (tap to swap)
      </div>
      <div className="flex flex-wrap gap-2">
        {filteredAlternatives.map((alt) => (
          <button
            key={alt.exerciseId}
            onClick={() => !disabled && onSelect(alt.exerciseId, alt.exerciseName)}
            disabled={disabled}
            className={`
              inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium
              transition-colors
              ${
                disabled
                  ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                  : 'bg-white border border-gray-200 text-gray-700 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700'
              }
            `}
          >
            <span className="truncate max-w-[150px]">{alt.exerciseName}</span>
            {alt.matchScore !== undefined && (
              <span className="ml-1.5 text-xs text-gray-400">({alt.matchScore}%)</span>
            )}
          </button>
        ))}
        {remainingCount > 0 && (
          <button
            onClick={onShowMore}
            disabled={disabled}
            className={`
              inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium
              transition-colors
              ${
                disabled
                  ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-50 text-blue-600 hover:bg-blue-100'
              }
            `}
          >
            +{remainingCount} more
          </button>
        )}
      </div>
    </div>
  )
}
