/**
 * Muscle Group Selector Component
 * Hierarchical selection of muscle groups
 */
import { useState, useMemo } from 'react'
import { MuscleGroup } from '../services/api'

interface MuscleGroupSelectorProps {
  muscleGroups: MuscleGroup[]
  selectedIds: number[]
  onChange: (selectedIds: number[]) => void
}

export default function MuscleGroupSelector({
  muscleGroups,
  selectedIds,
  onChange,
}: MuscleGroupSelectorProps) {
  const [expandedLevels, setExpandedLevels] = useState<Set<number>>(new Set([1]))

  // Organize muscle groups by level and parent
  const organizedGroups = useMemo(() => {
    const byLevel: Record<number, MuscleGroup[]> = {}
    const byParent: Record<number, MuscleGroup[]> = {}

    muscleGroups.forEach((mg) => {
      if (!byLevel[mg.level]) byLevel[mg.level] = []
      byLevel[mg.level].push(mg)

      const parentId = mg.parent_id || 0
      if (!byParent[parentId]) byParent[parentId] = []
      byParent[parentId].push(mg)
    })

    return { byLevel, byParent }
  }, [muscleGroups])

  const toggleLevel = (level: number) => {
    setExpandedLevels((prev) => {
      const next = new Set(prev)
      if (next.has(level)) {
        next.delete(level)
      } else {
        next.add(level)
      }
      return next
    })
  }

  const toggleMuscleGroup = (id: number) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((selectedId) => selectedId !== id))
    } else {
      onChange([...selectedIds, id])
    }
  }

  const renderLevel = (level: number, parentId: number | null = null) => {
    const groups = organizedGroups.byParent[parentId || 0] || []
    const levelGroups = groups.filter((mg) => mg.level === level)

    if (levelGroups.length === 0) return null

    return (
      <div className="ml-4 space-y-1">
        {levelGroups.map((mg) => {
          const isSelected = selectedIds.includes(mg.id)
          const hasChildren = (organizedGroups.byParent[mg.id] || []).length > 0
          const isExpanded = expandedLevels.has(level + 1)

          return (
            <div key={mg.id} className="flex items-start gap-2">
              <label className="flex items-center space-x-2 cursor-pointer py-1 flex-1">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={(e) => {
                    e.stopPropagation()
                    toggleMuscleGroup(mg.id)
                  }}
                  onClick={(e) => e.stopPropagation()}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className={`text-sm ${isSelected ? 'font-medium' : ''}`}>
                  {mg.name}
                </span>
              </label>
              {hasChildren && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleLevel(level + 1)
                  }}
                  className="ml-2 text-xs text-gray-500 hover:text-gray-700 px-1"
                >
                  {isExpanded ? '−' : '+'}
                </button>
              )}
            </div>
          )
        })}
        {expandedLevels.has(level + 1) &&
          levelGroups.map((mg) => {
            const children = organizedGroups.byParent[mg.id] || []
            if (children.length > 0) {
              return <div key={`children-${mg.id}`}>{renderLevel(level + 1, mg.id)}</div>
            }
            return null
          })}
      </div>
    )
  }

  return (
    <div className="border border-gray-300 rounded-md p-4 max-h-96 overflow-y-auto">
      <div className="space-y-2">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">
            Selected: {selectedIds.length}
          </span>
          {selectedIds.length > 0 && (
            <button
              onClick={() => onChange([])}
              className="text-xs text-red-600 hover:text-red-800"
            >
              Clear All
            </button>
          )}
        </div>

        {/* Level 1: Target Muscle Groups */}
        {renderLevel(1)}
      </div>
    </div>
  )
}
