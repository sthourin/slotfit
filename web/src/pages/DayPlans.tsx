import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useDayPlanStore } from '../stores/dayPlanStore'
import { useSessionStore } from '../stores/sessionStore'
import type { DayPlan, DayPlanInput, PatternGoal } from '../services/dayPlans'

const EMPTY: DayPlanInput = {
  name: '',
  description: null,
  warmup_preferences: [],
  rounds_target: 3,
  goals: [],
}

export default function DayPlans() {
  const { plans, patterns, loading, error, fetchAll, save, remove } = useDayPlanStore()
  const { start: startSession } = useSessionStore()
  const navigate = useNavigate()
  const [editing, setEditing] = useState<DayPlan | null>(null)
  const [draft, setDraft] = useState<DayPlanInput | null>(null)
  const [localError, setLocalError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  const openEditor = (plan?: DayPlan) => {
    setEditing(plan ?? null)
    setDraft(plan ? { ...plan, goals: plan.goals.map((g) => ({ ...g })) } : { ...EMPTY, goals: [] })
  }

  const toggleGoal = (patternId: number) => {
    if (!draft) return
    const has = draft.goals.some((g) => g.pattern_id === patternId)
    const goals: PatternGoal[] = has
      ? draft.goals.filter((g) => g.pattern_id !== patternId)
      : [...draft.goals, { pattern_id: patternId, required: true, target_sets: 3, rep_range_min: null, rep_range_max: null }]
    setDraft({ ...draft, goals })
  }

  const submit = async () => {
    if (!draft) return
    if (!draft.name.trim()) {
      setLocalError('Name is required.')
      return
    }
    setLocalError(null)
    try {
      await save(draft, editing?.id)
      setDraft(null)
      setEditing(null)
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Failed to save day plan')
    }
  }

  const handleStart = async (plan: DayPlan) => {
    setLocalError(null)
    setStarting(true)
    try {
      await startSession(plan.id)
      navigate('/session')
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setLocalError('A session is already in progress. Finish or discard it before starting a new one.')
      } else {
        setLocalError(err instanceof Error ? err.message : 'Failed to start session')
      }
    } finally {
      setStarting(false)
    }
  }

  const handleDelete = async (plan: DayPlan) => {
    if (!window.confirm(`Delete "${plan.name}"?`)) return
    setLocalError(null)
    try {
      await remove(plan.id)
    } catch (err) {
      // A plan any session was started from is refused with 409; without this
      // the dialog closes, the plan stays listed, and nothing explains why.
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setLocalError(
          `"${plan.name}" can't be deleted because training sessions reference it.`
        )
      } else {
        setLocalError(err instanceof Error ? err.message : 'Failed to delete day plan')
      }
    }
  }

  if (loading) return <div className="container mx-auto p-6">Loading day plans...</div>

  return (
    <div className="container mx-auto p-6 max-w-3xl">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Day Plans</h1>
        <button onClick={() => openEditor()} className="bg-blue-600 text-white px-4 py-2 rounded-md">
          New Day Plan
        </button>
      </div>
      {error && <div className="text-red-600 mb-4">{error}</div>}
      {localError && <div className="text-red-600 mb-4">{localError}</div>}

      {/* Cards stack on a phone: side by side, the pattern list and the three
          buttons overlapped each other at 390px. */}
      {plans.map((plan) => (
        <div
          key={plan.id}
          className="bg-white rounded-lg shadow p-4 mb-3 flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center"
        >
          <div className="min-w-0">
            <div className="font-semibold">{plan.name}</div>
            <div className="text-sm text-gray-500">
              {plan.rounds_target} rounds ·{' '}
              {plan.goals
                .map((g) => patterns.find((p) => p.id === g.pattern_id)?.name ?? g.pattern_id)
                .join(', ')}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => handleStart(plan)}
              disabled={starting}
              className="bg-green-600 text-white px-3 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Start Session
            </button>
            <button onClick={() => openEditor(plan)} className="text-blue-600 px-3 py-2">Edit</button>
            <button onClick={() => handleDelete(plan)} className="text-red-500 px-3 py-2">Delete</button>
          </div>
        </div>
      ))}
      {plans.length === 0 && <p className="text-gray-500">No day plans yet. Create one to get started.</p>}

      {draft && (
        <div className="bg-white rounded-lg shadow p-6 mt-6">
          <h2 className="text-lg font-semibold mb-4">{editing ? 'Edit Day Plan' : 'New Day Plan'}</h2>
          <label className="block mb-3">
            <span className="text-sm text-gray-600">Name</span>
            <input
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              className="mt-1 w-full border rounded-md px-3 py-2"
              placeholder="e.g. Full Body A"
            />
          </label>
          <label className="block mb-3">
            <span className="text-sm text-gray-600">Rounds target</span>
            <input
              type="number"
              min={1}
              max={10}
              value={draft.rounds_target}
              onChange={(e) => {
                if (e.target.value === '') return
                setDraft({ ...draft, rounds_target: Number(e.target.value) })
              }}
              className="mt-1 w-24 border rounded-md px-3 py-2"
            />
          </label>
          <div className="mb-4">
            <span className="text-sm text-gray-600 block mb-2">Pattern goals</span>
            {/* Every pattern is selectable, conditioning included. It was once
                excluded on the assumption that conditioning is only ever the
                warm-up, but interval work (rower, HIIT AMRAP circuits) is real
                training with its own volume worth planning for. */}
            {patterns
              .map((p) => {
                const goal = draft.goals.find((g) => g.pattern_id === p.id)
                return (
                  <div key={p.id} className="flex items-center gap-3 py-1">
                    <label className="flex items-center gap-2 flex-1">
                      <input type="checkbox" checked={!!goal} onChange={() => toggleGoal(p.id)} />
                      {p.name}
                    </label>
                    {goal && (
                      <>
                        <label className="text-sm flex items-center gap-1">
                          <input
                            type="checkbox"
                            checked={goal.required}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                goals: draft.goals.map((g) =>
                                  g.pattern_id === p.id ? { ...g, required: e.target.checked } : g
                                ),
                              })
                            }
                          />
                          required
                        </label>
                        <input
                          type="number"
                          min={1}
                          max={30}
                          value={goal.target_sets ?? 3}
                          onChange={(e) => {
                            if (e.target.value === '') return
                            setDraft({
                              ...draft,
                              goals: draft.goals.map((g) =>
                                g.pattern_id === p.id ? { ...g, target_sets: Number(e.target.value) } : g
                              ),
                            })
                          }}
                          className="w-16 border rounded-md px-2 py-1 text-sm"
                          title="Target sets"
                        />
                      </>
                    )}
                  </div>
                )
              })}
          </div>
          <div className="space-x-2">
            <button onClick={submit} className="bg-blue-600 text-white px-4 py-2 rounded-md">
              {editing ? 'Save Changes' : 'Create Day Plan'}
            </button>
            <button onClick={() => { setDraft(null); setEditing(null) }} className="text-gray-600 px-3">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
