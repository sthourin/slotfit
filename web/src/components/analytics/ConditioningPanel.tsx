/**
 * This week's conditioning: duration, distance, pace, and load-distance.
 *
 * Sits beside the volume chart rather than inside it. Tonnage and distance do
 * not share a unit, and folding them together would let a single 5km ruck
 * outweigh a month of lifting - so the two are reported side by side and each
 * stays readable. Tracking both is the point of the app.
 */
import type { WeeklyConditioningResponse } from '../../services/analytics'

interface Props {
  data: WeeklyConditioningResponse
}

/** Seconds as h:mm:ss or m:ss - a ruck runs to hours, an interval to seconds. */
function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

/** Metres below 1km, kilometres above, at one decimal. */
function formatDistance(meters: number): string {
  if (meters === 0) return '—'
  return meters < 1000 ? `${Math.round(meters)}m` : `${(meters / 1000).toFixed(2)}km`
}

/** Pace as m:ss per km, the unit it is actually spoken in. */
function formatPace(secondsPerKm: number | null): string {
  if (secondsPerKm == null) return '—'
  const m = Math.floor(secondsPerKm / 60)
  const s = Math.round(secondsPerKm % 60)
  return `${m}:${String(s).padStart(2, '0')} /km`
}

/**
 * Load-distance in thousands, because the raw number is enormous and its
 * absolute value means little - it is for comparing weeks, not for reading.
 */
function formatLoadMeters(loadMeters: number): string {
  if (loadMeters === 0) return '—'
  return `${Math.round(loadMeters / 1000).toLocaleString()}k`
}

export default function ConditioningPanel({ data }: Props) {
  if (data.total_sets === 0) {
    return (
      <div className="bg-white rounded-lg border p-4">
        <h3 className="font-semibold mb-1">Conditioning</h3>
        <p className="text-sm text-gray-500">
          No conditioning logged this week. Rows, rucks, carries and holds appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="font-semibold mb-3">Conditioning</h3>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <div>
          <div className="text-xs text-gray-500 uppercase">Time</div>
          <div className="text-lg font-semibold">{formatDuration(data.total_seconds)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase">Distance</div>
          <div className="text-lg font-semibold">{formatDistance(data.total_meters)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase">Pace</div>
          <div className="text-lg font-semibold">{formatPace(data.pace_seconds_per_km)}</div>
        </div>
        <div>
          {/* Distinct from tonnage on purpose: this is load carried over ground,
              which is why it is named for its units rather than called volume. */}
          <div className="text-xs text-gray-500 uppercase" title="Effective load x distance">
            Load·distance
          </div>
          <div className="text-lg font-semibold">{formatLoadMeters(data.load_meters)}</div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 uppercase border-b">
              <th className="py-1 pr-2">Exercise</th>
              <th className="py-1 pr-2 text-right">Sets</th>
              <th className="py-1 pr-2 text-right">Time</th>
              <th className="py-1 pr-2 text-right">Distance</th>
              <th className="py-1 text-right">Pace</th>
            </tr>
          </thead>
          <tbody>
            {data.by_exercise.map((row) => (
              <tr key={row.exercise_id} className="border-b last:border-0">
                <td className="py-2 pr-2">{row.name}</td>
                <td className="py-2 pr-2 text-right">{row.sets}</td>
                <td className="py-2 pr-2 text-right">{formatDuration(row.seconds)}</td>
                <td className="py-2 pr-2 text-right">{formatDistance(row.meters)}</td>
                <td className="py-2 text-right">{formatPace(row.pace_seconds_per_km)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
