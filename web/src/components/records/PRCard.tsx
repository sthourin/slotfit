/**
 * PR Card Component
 * Displays a personal record card for an exercise
 */
import { type PersonalRecord } from '../../services/personalRecords'
import { type Exercise } from '../../services/exercises'

interface PRCardProps {
  exercise: Exercise | undefined
  exerciseId: number
  latestPR: PersonalRecord
  allRecords: PersonalRecord[]
  onClick: () => void
}

export default function PRCard({
  exercise,
  exerciseId,
  latestPR,
  allRecords,
  onClick,
}: PRCardProps) {
  const getPRTypeLabel = (type: string) => {
    switch (type) {
      case 'weight':
        return 'Max Weight'
      case 'reps':
        return 'Max Reps'
      case 'volume':
        return 'Max Volume'
      case 'time':
        return 'Best Time'
      default:
        return type
    }
  }

  const getPRTypeUnit = (type: string) => {
    switch (type) {
      case 'weight':
        return ' lbs'
      case 'reps':
        return ' reps'
      case 'volume':
        return ' lbs'
      case 'time':
        return ' sec'
      default:
        return ''
    }
  }

  const getPRTypeColor = (type: string) => {
    switch (type) {
      case 'weight':
        return 'bg-blue-100 text-blue-800'
      case 'reps':
        return 'bg-purple-100 text-purple-800'
      case 'volume':
        return 'bg-green-100 text-green-800'
      case 'time':
        return 'bg-orange-100 text-orange-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow cursor-pointer border border-gray-200"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-lg font-semibold mb-2">
            {exercise?.name || `Exercise ${exerciseId}`}
          </h3>
          <div className="space-y-2">
            {allRecords.map((pr) => {
              const isLatest = pr.id === latestPR.id
              return (
                <div
                  key={pr.id}
                  className={`flex items-center justify-between p-2 rounded ${
                    isLatest ? 'bg-yellow-50 border border-yellow-200' : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded ${getPRTypeColor(pr.record_type)}`}
                    >
                      {getPRTypeLabel(pr.record_type)}
                    </span>
                    {isLatest && (
                      <span className="px-2 py-1 text-xs bg-yellow-200 text-yellow-900 rounded font-medium">
                        Latest
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-lg">
                      {pr.value.toLocaleString()}
                      {getPRTypeUnit(pr.record_type)}
                    </div>
                    <div className="text-xs text-gray-500">
                      {new Date(pr.achieved_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
        <div className="ml-4 text-gray-400">
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
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </div>
    </div>
  )
}
