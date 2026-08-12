/**
 * Bodyweight readings, newest first, with a single-field add.
 *
 * A log rather than one editable number: bodyweight drifts, and every past set
 * is scored against the reading in effect when it was performed, so replacing a
 * single value would silently rewrite years of volume and e1RM. Health Connect
 * will write here too, which is why entries show their source.
 */
import { useEffect, useState } from 'react'
import {
  createReading,
  deleteReading,
  listReadings,
  type BodyweightReading,
} from '../../services/bodyweight'

function BodyweightSection() {
  const [readings, setReadings] = useState<BodyweightReading[]>([])
  const [weight, setWeight] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const refresh = async () => {
    try {
      setReadings(await listReadings())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load readings')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const add = async () => {
    const value = Number(weight)
    if (!Number.isFinite(value) || value <= 0) {
      setError('Enter a weight greater than zero.')
      return
    }
    setError(null)
    setBusy(true)
    try {
      await createReading(value)
      setWeight('')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save reading')
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id: number) => {
    setBusy(true)
    try {
      await deleteReading(id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete reading')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-1">Bodyweight</h2>
      <p className="text-sm text-gray-500 mb-4">
        Used to score bodyweight exercises. Each set is measured against the reading in effect
        on the day you performed it, so adding one never changes what past sets meant.
      </p>

      <div className="flex flex-wrap gap-2 items-center mb-3">
        <input
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') add()
          }}
          placeholder="weight"
          aria-label="bodyweight"
          inputMode="decimal"
          className="w-28 border rounded-md px-3 py-3 min-h-[44px]"
        />
        <button
          onClick={add}
          disabled={busy || weight.trim() === ''}
          className="bg-blue-600 text-white px-5 py-3 min-h-[44px] rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add
        </button>
      </div>

      {error && (
        <div className="text-red-600 text-sm mb-2" role="alert">
          {error}
        </div>
      )}

      {loading && <p className="text-sm text-gray-400">Loading...</p>}

      {!loading && readings.length === 0 && (
        <p className="text-sm text-gray-400">
          No readings yet. Bodyweight exercises are left out of strength trends and volume
          until you add one &mdash; a guessed bodyweight would be worse than none.
        </p>
      )}

      <ul className="divide-y">
        {readings.map((r) => (
          <li key={r.id} className="flex justify-between items-center py-2 gap-2">
            <span className="min-w-0">
              <span className="font-medium">{r.weight}</span>
              <span className="text-sm text-gray-500 ml-2">
                {new Date(r.recorded_at).toLocaleDateString()}
              </span>
              {r.source !== 'manual' && (
                <span className="text-xs text-gray-400 ml-2">{r.source}</span>
              )}
            </span>
            <button
              onClick={() => remove(r.id)}
              disabled={busy}
              className="text-red-500 px-3 py-2 shrink-0 disabled:opacity-50"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default BodyweightSection
