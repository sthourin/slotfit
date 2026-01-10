/**
 * PR History Component
 * Shows detailed history of personal records for an exercise
 */
import { type PersonalRecord } from '../../services/personalRecords'
import { type Exercise } from '../../services/exercises'

interface PRHistoryProps {
  records: PersonalRecord[]
  exercise: Exercise | undefined
}

export default function PRHistory({ records, exercise: _exercise }: PRHistoryProps) {
  const sortedRecords = [...records].sort(
    (a, b) => new Date(b.achieved_at).getTime() - new Date(a.achieved_at).getTime()
  )

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

  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <h4 className="font-semibold mb-3 text-gray-700">PR History</h4>
      <div className="space-y-2">
        {sortedRecords.map((pr) => (
          <div
            key={pr.id}
            className="bg-white rounded p-3 border border-gray-200 flex items-center justify-between"
          >
            <div>
              <div className="font-medium text-sm">
                {getPRTypeLabel(pr.record_type)}
              </div>
              {pr.context && Object.keys(pr.context).length > 0 && (
                <div className="text-xs text-gray-500 mt-1">
                  {JSON.stringify(pr.context)}
                </div>
              )}
            </div>
            <div className="text-right">
              <div className="font-bold">
                {pr.value.toLocaleString()}
                {getPRTypeUnit(pr.record_type)}
              </div>
              <div className="text-xs text-gray-500">
                {new Date(pr.achieved_at).toLocaleString()}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
