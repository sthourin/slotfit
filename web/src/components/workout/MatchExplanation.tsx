/**
 * MatchExplanation - Shows why an exercise matches the slot specification
 */
import type { Exercise } from '../../services/exercises'

interface MuscleGroup {
  id: number
  name: string
}

interface MatchExplanationProps {
  exercise: Exercise
  primaryMuscleGroup: MuscleGroup | null
  secondaryMuscleGroups: MuscleGroup[]
  lastPerformed?: string | null // ISO date string
  isExpanded?: boolean
}

export default function MatchExplanation({
  exercise,
  primaryMuscleGroup,
  secondaryMuscleGroups,
  lastPerformed,
  isExpanded = true,
}: MatchExplanationProps) {
  const reasons: string[] = []

  // Primary muscle group match
  if (primaryMuscleGroup) {
    const exerciseMuscleIds = exercise.muscle_groups?.map((mg) => mg.id) || []
    if (exerciseMuscleIds.includes(primaryMuscleGroup.id)) {
      reasons.push(`Hits primary target: ${primaryMuscleGroup.name}`)
    }
  }

  // Secondary muscle group matches
  if (secondaryMuscleGroups.length > 0) {
    const exerciseMuscleIds = exercise.muscle_groups?.map((mg) => mg.id) || []
    const matchingSecondary = secondaryMuscleGroups.filter((mg) =>
      exerciseMuscleIds.includes(mg.id)
    )
    if (matchingSecondary.length > 0) {
      const names = matchingSecondary.map((mg) => mg.name).join(', ')
      reasons.push(`Also works secondary targets: ${names}`)
    }
  }

  // Movement type
  if (exercise.mechanics) {
    reasons.push(`${exercise.mechanics} movement`)
  }

  // Equipment
  if (exercise.primary_equipment) {
    reasons.push(`Uses ${exercise.primary_equipment.name}`)
  } else {
    reasons.push('Bodyweight - always available')
  }

  // Last performed / recovery
  if (lastPerformed) {
    const daysSince = getDaysSince(lastPerformed)
    if (daysSince === 0) {
      reasons.push('Done today')
    } else if (daysSince === 1) {
      reasons.push('Done yesterday')
    } else {
      reasons.push(`Last performed ${daysSince} days ago`)
    }
  } else {
    reasons.push('Never performed - adds variety')
  }

  if (!isExpanded) {
    // Collapsed view - just show a summary
    return (
      <div className="text-sm text-gray-500">
        {reasons.slice(0, 2).join(' | ')}
        {reasons.length > 2 && '...'}
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
        Why This Fits
      </h4>
      <ul className="text-sm text-gray-600 space-y-0.5">
        {reasons.map((reason, index) => (
          <li key={index} className="flex items-start">
            <span className="text-green-500 mr-2">-</span>
            {reason}
          </li>
        ))}
      </ul>
    </div>
  )
}

function getDaysSince(dateString: string): number {
  const date = new Date(dateString)
  const now = new Date()
  const diffTime = Math.abs(now.getTime() - date.getTime())
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
  return diffDays
}
