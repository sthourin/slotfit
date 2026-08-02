/**
 * One exercise inside a superset round: shows the progression target and
 * logs sets.
 *
 * Weight / reps / time are all optional — bodyweight work has no weight, and
 * the warm-up (rower, bike, jump rope) is logged purely as `time_seconds`.
 * The Log Set button is disabled while a mutation is in flight so a sweaty
 * double-tap cannot record a duplicate set.
 */
import { useState } from 'react'
import type { RoundEntry } from '../../services/sessions'

interface Props {
  entry: RoundEntry
  onLogSet: (
    entryId: number,
    set: {
      set_number: number
      weight?: number | null
      reps?: number | null
      time_seconds?: number | null
    }
  ) => Promise<unknown>
  busy?: boolean
  /**
   * Failure message for this entry's last set. Rendered inside the card rather
   * than in a page-level banner: several rounds deep on a phone, the top of the
   * page is off-screen and a failed set would otherwise just silently not appear.
   */
  error?: string | null
}

/** "8 @ 135", "12", "45s" — never "null" or a misleading 0. */
function formatSet(s: { weight: number | null; reps: number | null; time_seconds: number | null }): string {
  const bits: string[] = []
  if (s.reps != null) bits.push(s.weight != null ? `${s.reps} @ ${s.weight}` : `${s.reps}`)
  else if (s.weight != null) bits.push(`@ ${s.weight}`)
  if (s.time_seconds != null) bits.push(`${s.time_seconds}s`)
  return bits.length > 0 ? bits.join(' · ') : '—'
}

export default function EntryCard({ entry, onLogSet, busy, error }: Props) {
  const [weight, setWeight] = useState<string>(
    entry.target?.weight != null ? String(entry.target.weight) : ''
  )
  const [reps, setReps] = useState<string>(entry.target ? String(entry.target.reps) : '')
  const [timeSec, setTimeSec] = useState<string>('')

  const parse = (v: string): number | null => {
    if (v.trim() === '') return null
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }

  const logSet = async () => {
    await onLogSet(entry.id, {
      set_number: entry.sets.length + 1,
      weight: parse(weight),
      reps: parse(reps),
      time_seconds: parse(timeSec),
    })
  }

  const target = entry.target

  return (
    <div className="bg-white rounded-lg border p-4 mb-2">
      <div className="flex justify-between items-start gap-2">
        <div>
          <span className="text-xs text-gray-400 uppercase mr-2">#{entry.position}</span>
          <span className="font-semibold">{entry.exercise_name}</span>
          <span className="ml-2 text-xs text-gray-500">{entry.pattern_slug.replace(/_/g, ' ')}</span>
        </div>
        <span className="text-sm text-gray-500 whitespace-nowrap">{entry.sets.length} sets</span>
      </div>

      {target && (
        <div className="text-sm text-gray-500 mt-1">
          {target.last_summary ? `Last: ${target.last_summary} → ` : ''}
          Target: {target.sets}x{target.reps}
          {target.weight != null ? ` @ ${target.weight}` : ''}
        </div>
      )}
      {!target && <div className="text-sm text-gray-400 mt-1">No history yet — log your first set.</div>}

      {/* Touch heights are deliberately generous (>= 44px): this row is tapped
          dozens of times per session, one-handed, with sweaty hands. */}
      <div className="flex flex-wrap gap-2 mt-3 items-center">
        <input
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
          placeholder="weight"
          aria-label="weight"
          className="w-24 border rounded-md px-3 py-3 min-h-[44px]"
          inputMode="decimal"
        />
        <input
          value={reps}
          onChange={(e) => setReps(e.target.value)}
          placeholder="reps"
          aria-label="reps"
          className="w-20 border rounded-md px-3 py-3 min-h-[44px]"
          inputMode="numeric"
        />
        <input
          value={timeSec}
          onChange={(e) => setTimeSec(e.target.value)}
          placeholder="time (sec)"
          aria-label="time (sec)"
          className="w-28 border rounded-md px-3 py-3 min-h-[44px]"
          inputMode="numeric"
        />
        <button
          onClick={logSet}
          disabled={busy}
          className="bg-blue-600 text-white px-5 py-3 min-h-[44px] rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Log Set
        </button>
      </div>

      {error && (
        <div className="text-red-600 text-sm mt-2" role="alert">
          {error}
        </div>
      )}

      {entry.sets.length > 0 && (
        <div className="text-sm text-gray-600 mt-2">
          {entry.sets.map((s) => formatSet(s)).join(', ')}
        </div>
      )}
    </div>
  )
}
