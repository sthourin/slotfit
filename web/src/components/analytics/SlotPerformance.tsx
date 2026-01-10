/**
 * Slot Performance Component
 * Shows performance metrics for each slot in a routine
 */
import { type SlotPerformanceResponse } from '../../services/analytics'

interface SlotPerformanceProps {
  data: SlotPerformanceResponse
}

export default function SlotPerformance({ data }: SlotPerformanceProps) {
  if (data.slots.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No performance data available for this routine yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {data.slots.map((slot) => (
        <div key={slot.slot_id} className="border rounded-lg p-4">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h4 className="font-semibold text-lg">
                {slot.slot_name || `Slot ${slot.slot_id}`}
              </h4>
              <p className="text-sm text-gray-600">
                Performed {slot.times_performed} time{slot.times_performed !== 1 ? 's' : ''}
              </p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-blue-600">
                {(slot.completion_rate * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-gray-500">Completion Rate</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-4">
            <div>
              <div className="text-sm text-gray-600">Average Sets</div>
              <div className="text-lg font-semibold">{slot.average_sets.toFixed(1)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Most Used Exercise</div>
              <div className="text-lg font-semibold">
                {slot.most_used_exercise_name || 'N/A'}
              </div>
            </div>
          </div>

          {/* Completion Rate Bar */}
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${slot.completion_rate * 100}%` }}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
