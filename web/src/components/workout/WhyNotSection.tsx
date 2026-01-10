/**
 * Why Not Section Component
 * Expandable section showing exercises that were filtered out and why
 */
import { useState } from 'react'
import { type NotRecommendedExercise } from '../../services/recommendations'

interface WhyNotSectionProps {
  notRecommended: NotRecommendedExercise[]
}

export default function WhyNotSection({ notRecommended }: WhyNotSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (notRecommended.length === 0) return null

  // Group by reason type for better organization
  const groupedByReason = notRecommended.reduce((acc, item) => {
    const reasonType = item.reason.split(':')[0] || item.reason
    if (!acc[reasonType]) {
      acc[reasonType] = []
    }
    acc[reasonType].push(item)
    return acc
  }, {} as Record<string, NotRecommendedExercise[]>)

  return (
    <div className="border rounded-lg">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">
            Why Not These Exercises?
          </span>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {notRecommended.length} filtered
          </span>
        </div>
        <svg
          className={`w-5 h-5 text-gray-500 transition-transform ${
            isExpanded ? 'transform rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="border-t p-4 bg-gray-50">
          <div className="space-y-4">
            {Object.entries(groupedByReason).map(([reasonType, exercises]) => (
              <div key={reasonType}>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">{reasonType}</h4>
                <div className="space-y-2">
                  {exercises.map((item) => (
                    <div
                      key={item.exercise_id}
                      className="flex items-start justify-between p-3 bg-white rounded border border-gray-200"
                    >
                      <div className="flex-1">
                        <div className="font-medium text-sm">{item.exercise_name}</div>
                        <div className="text-xs text-gray-600 mt-1">{item.reason}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
