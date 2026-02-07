/**
 * SlotSpecificationCard - Primary slot spec display showing what the slot requires
 * This is the "hero" component that makes the slot specification front-and-center
 */
import type { SlotType } from '../../services/routines'
import SlotTypeIndicator, { getSlotTypeConfig } from './SlotTypeIndicator'
import SlotTargets from './SlotTargets'

interface MuscleGroup {
  id: number
  name: string
}

interface SlotSpecificationCardProps {
  slotNumber: number
  slotName: string | null
  slotType: SlotType
  primaryMuscleGroup: MuscleGroup | null
  secondaryMuscleGroups: MuscleGroup[]
  workoutStyle: string | null
  targetSets: number | null
  targetRepsMin: number | null
  targetRepsMax: number | null
  targetWeight: number | null
  targetRestSeconds: number | null
  completedSets?: number
  slotState?: 'not_started' | 'in_progress' | 'completed' | 'skipped'
}

export default function SlotSpecificationCard({
  slotNumber,
  slotName,
  slotType,
  primaryMuscleGroup,
  secondaryMuscleGroups,
  workoutStyle,
  targetSets,
  targetRepsMin,
  targetRepsMax,
  targetWeight,
  targetRestSeconds,
  completedSets,
  slotState,
}: SlotSpecificationCardProps) {
  const config = getSlotTypeConfig(slotType)

  return (
    <div
      className={`
        rounded-lg border-2 p-4
        ${config.borderColor} ${config.bgColor}
      `}
    >
      {/* Header: Slot number/name and type indicator */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-bold text-gray-900">
            {slotName || `Slot ${slotNumber}`}
          </h2>
          {slotState === 'in_progress' && (
            <span className="text-sm text-blue-600 font-medium">(In Progress)</span>
          )}
          {slotState === 'completed' && (
            <span className="text-sm text-green-600 font-medium">(Completed)</span>
          )}
        </div>
        <SlotTypeIndicator slotType={slotType} />
      </div>

      {/* Slot type description for non-standard types */}
      {config.description && (
        <p className="text-sm text-gray-600 mb-4 italic">{config.description}</p>
      )}

      {/* Muscle Groups: Primary and Secondary */}
      <div className="mb-4">
        {primaryMuscleGroup ? (
          <div className="space-y-2">
            <div>
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Primary Target
              </span>
              <div className="mt-1">
                <span className="inline-block px-4 py-2 bg-white border-2 border-gray-300 rounded-lg text-lg font-bold text-gray-900 shadow-sm">
                  {primaryMuscleGroup.name}
                </span>
              </div>
            </div>
            {secondaryMuscleGroups.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Secondary Targets
                </span>
                <div className="mt-1 flex flex-wrap gap-2">
                  {secondaryMuscleGroups.map((mg) => (
                    <span
                      key={mg.id}
                      className="inline-block px-3 py-1 bg-white border border-gray-200 rounded-md text-sm text-gray-700"
                    >
                      {mg.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : secondaryMuscleGroups.length > 0 ? (
          // Fallback: show all muscle groups as targets (for backward compat)
          <div>
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Target Muscles
            </span>
            <div className="mt-1 flex flex-wrap gap-2">
              {secondaryMuscleGroups.map((mg) => (
                <span
                  key={mg.id}
                  className="inline-block px-3 py-1.5 bg-white border border-gray-200 rounded-md text-sm font-medium text-gray-700"
                >
                  {mg.name}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-sm text-gray-500 italic">No target muscles specified</div>
        )}
      </div>

      {/* Targets: Sets, Reps, Weight, Rest, Style */}
      <SlotTargets
        targetSets={targetSets}
        targetRepsMin={targetRepsMin}
        targetRepsMax={targetRepsMax}
        targetWeight={targetWeight}
        targetRestSeconds={targetRestSeconds}
        workoutStyle={workoutStyle}
        completedSets={completedSets}
      />
    </div>
  )
}
