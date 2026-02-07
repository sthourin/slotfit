/**
 * SlotTargets - Displays target sets, reps, weight, and rest for a slot
 */

interface SlotTargetsProps {
  targetSets: number | null
  targetRepsMin: number | null
  targetRepsMax: number | null
  targetWeight: number | null
  targetRestSeconds: number | null
  workoutStyle: string | null
  completedSets?: number
  compact?: boolean
}

export default function SlotTargets({
  targetSets,
  targetRepsMin,
  targetRepsMax,
  targetWeight,
  targetRestSeconds,
  workoutStyle,
  completedSets,
  compact = false,
}: SlotTargetsProps) {
  const hasTargets = targetSets || targetRepsMin || targetRepsMax || targetWeight || targetRestSeconds || workoutStyle

  if (!hasTargets) {
    return null
  }

  // Format rep range
  const getRepRange = () => {
    if (targetRepsMin && targetRepsMax) {
      if (targetRepsMin === targetRepsMax) {
        return `${targetRepsMin} reps`
      }
      return `${targetRepsMin}-${targetRepsMax} reps`
    }
    if (targetRepsMin) return `${targetRepsMin}+ reps`
    if (targetRepsMax) return `up to ${targetRepsMax} reps`
    return null
  }

  // Format rest time
  const formatRest = (seconds: number) => {
    if (seconds >= 60) {
      const minutes = Math.floor(seconds / 60)
      const remainingSeconds = seconds % 60
      if (remainingSeconds === 0) {
        return `${minutes}m rest`
      }
      return `${minutes}m ${remainingSeconds}s rest`
    }
    return `${seconds}s rest`
  }

  const repRange = getRepRange()

  if (compact) {
    // Compact inline view
    const parts: string[] = []
    if (targetSets) parts.push(`${targetSets} sets`)
    if (repRange) parts.push(repRange)
    if (targetWeight) parts.push(`${targetWeight} lbs`)
    if (targetRestSeconds) parts.push(formatRest(targetRestSeconds))

    return (
      <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
        {workoutStyle && (
          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
            {workoutStyle}
          </span>
        )}
        {parts.length > 0 && <span>{parts.join(' | ')}</span>}
      </div>
    )
  }

  // Full view with pills
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {workoutStyle && (
          <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-md text-sm font-medium">
            {workoutStyle}
          </span>
        )}
        {targetSets && (
          <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md text-sm">
            {targetSets} sets
            {completedSets !== undefined && (
              <span className="ml-1 text-gray-500">({completedSets}/{targetSets})</span>
            )}
          </span>
        )}
        {repRange && (
          <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md text-sm">
            {repRange}
          </span>
        )}
        {targetWeight && (
          <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md text-sm">
            {targetWeight} lbs
          </span>
        )}
      </div>
      {targetRestSeconds && (
        <div className="text-sm text-gray-500">
          Rest: {formatRest(targetRestSeconds)} between sets
        </div>
      )}
    </div>
  )
}
