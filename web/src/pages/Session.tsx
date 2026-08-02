/**
 * The in-gym session screen.
 *
 * Flow: optional warm-up card → rounds (pick an anchor from whatever station
 * is free, then a partner working the opposite pattern, optionally a third) →
 * log sets per entry → finish with a summary.
 *
 * Every mutating control binds `disabled` to the store's `busy` flag: this is
 * used one-handed and sweaty, and a double-tap on "Log Set" would otherwise
 * record a real duplicate set. Failures surface in a banner rather than
 * silently doing nothing, because gym wifi is unreliable.
 */
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useSessionStore } from '../stores/sessionStore'
import { useDayPlanStore } from '../stores/dayPlanStore'
import { getAnchorSuggestions, getPartnerSuggestions } from '../services/suggestions'
import type { AnchorSuggestions, PartnerSuggestions, SuggestionCard } from '../services/suggestions'
import { exerciseApi } from '../services/exercises'
import { listStaples, createStaple } from '../services/staples'
import type { Staple } from '../services/staples'
import CoverageChips from '../components/session/CoverageChips'
import SuggestionList from '../components/session/SuggestionList'
import EntryCard from '../components/session/EntryCard'

type Picker =
  | { kind: 'anchor'; roundId: number }
  | { kind: 'partner'; roundId: number; anchorExerciseId: number; position: 2 | 3 }
  | null

interface WarmupOption {
  id: number
  name: string
}

const message = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback)

export default function Session() {
  const { session, coverage, busy, error, resume, addRound, addEntry, logSet, complete, discard } =
    useSessionStore()
  const plans = useDayPlanStore((s) => s.plans)
  const fetchPlans = useDayPlanStore((s) => s.fetchAll)
  const navigate = useNavigate()

  const [picker, setPicker] = useState<Picker>(null)
  const [anchorData, setAnchorData] = useState<AnchorSuggestions | null>(null)
  const [partnerData, setPartnerData] = useState<PartnerSuggestions | null>(null)
  const [suggestionError, setSuggestionError] = useState<string | null>(null)
  const [finished, setFinished] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const [resumeChecked, setResumeChecked] = useState(false)
  const [warmups, setWarmups] = useState<WarmupOption[]>([])
  const [warmupError, setWarmupError] = useState<string | null>(null)
  const [staples, setStaples] = useState<Staple[]>([])
  const [staplesLoaded, setStaplesLoaded] = useState(false)
  const [staplesError, setStaplesError] = useState<string | null>(null)
  const [stapling, setStapling] = useState<number | null>(null)
  // Set-logging failures are reported inside the EntryCard that failed: three
  // rounds deep on a phone, a banner at the top of the page is off-screen.
  const [entryError, setEntryError] = useState<{ entryId: number; message: string } | null>(null)

  const sessionId = session?.id ?? null
  const dayPlanId = session?.day_plan_id ?? null
  const dayPlan = plans.find((p) => p.id === dayPlanId) ?? null
  const warmupKey = (dayPlan?.warmup_preferences ?? []).join(',')
  // Groups with no staples are dropped server-side, so an empty staple pool
  // arrives here as `groups: []` and the picker would otherwise render nothing.
  const anchorCardCount = (anchorData?.groups ?? []).reduce((n, g) => n + g.staples.length, 0)

  // Resume an in-progress session when the page is opened cold (refresh, or
  // the phone screen locking mid-workout).
  useEffect(() => {
    if (session) {
      setResumeChecked(true)
      return
    }
    if (resumeChecked) return
    resume()
      .catch(() => undefined)
      .finally(() => setResumeChecked(true))
  }, [session, resume, resumeChecked])

  // Day plans supply the warm-up preferences; the user may have landed here
  // directly without visiting the Day Plans page first.
  useEffect(() => {
    if (plans.length === 0) fetchPlans()
  }, [plans.length, fetchPlans])

  useEffect(() => {
    if (warmupKey === '') {
      setWarmups([])
      setWarmupError(null)
      return
    }
    let cancelled = false
    setWarmupError(null)
    Promise.all(warmupKey.split(',').map((id) => exerciseApi.get(Number(id))))
      .then((list) => {
        if (!cancelled) setWarmups(list.map((e) => ({ id: e.id, name: e.name })))
      })
      .catch((e) => {
        if (cancelled) return
        setWarmups([])
        setWarmupError(message(e, 'Could not load your warm-up options.'))
      })
    return () => {
      cancelled = true
    }
  }, [warmupKey])

  // Keyed on session *id* rather than the session object so that refreshing
  // after each logged set does not re-fetch suggestions underneath the user.
  useEffect(() => {
    if (!picker || sessionId == null) return
    let cancelled = false
    setSuggestionError(null)
    if (picker.kind === 'anchor') {
      setAnchorData(null)
      getAnchorSuggestions(sessionId)
        .then((d) => {
          if (!cancelled) setAnchorData(d)
        })
        .catch((e) => {
          if (!cancelled) setSuggestionError(message(e, 'Failed to load anchor suggestions'))
        })
    } else {
      setPartnerData(null)
      getPartnerSuggestions(sessionId, picker.anchorExerciseId, picker.position)
        .then((d) => {
          if (!cancelled) setPartnerData(d)
        })
        .catch((e) => {
          if (!cancelled) setSuggestionError(message(e, 'Failed to load partner suggestions'))
        })
    }
    return () => {
      cancelled = true
    }
  }, [picker, sessionId])

  // The staple list decides which exercises are offered as "new". If the fetch
  // fails we must not present the list at all: an empty `staples` would offer
  // every exercise, including ones already stapled, which 4xx on tap.
  useEffect(() => {
    if (!finished) return
    setStaplesError(null)
    listStaples()
      .then((s) => {
        setStaples(s)
        setStaplesLoaded(true)
      })
      .catch((e) => {
        setStaplesError(message(e, 'Could not check which exercises are already staples.'))
      })
  }, [finished])

  const handleLogSet = useCallback(
    async (
      entryId: number,
      s: { set_number: number; weight?: number | null; reps?: number | null; time_seconds?: number | null }
    ) => {
      setLocalError(null)
      try {
        await logSet(entryId, s)
        setEntryError((prev) => (prev?.entryId === entryId ? null : prev))
      } catch (e) {
        setEntryError({
          entryId,
          message: message(e, 'Failed to log set. Check your connection and try again.'),
        })
      }
    },
    [logSet]
  )

  if (!session) {
    if (!resumeChecked) {
      return <div className="container mx-auto p-6">Loading session...</div>
    }
    return (
      <div className="container mx-auto p-6">
        {/* A failed check is not the same as "no session": say so, or the user
            starts a new one and gets an unexplained 409. */}
        {error ? (
          <p className="text-red-600">{error}</p>
        ) : (
          <p className="text-gray-500">No active session.</p>
        )}
        <button onClick={() => navigate('/')} className="text-blue-600 underline mt-2 py-2">
          Pick a day plan to start
        </button>
      </div>
    )
  }

  const startRound = async () => {
    setLocalError(null)
    try {
      const roundId = await addRound()
      setPicker({ kind: 'anchor', roundId })
    } catch (e) {
      setLocalError(message(e, 'Failed to start the round'))
    }
  }

  const startWarmup = async (exerciseId: number) => {
    setLocalError(null)
    try {
      const roundId = await addRound()
      await addEntry(roundId, exerciseId, 1)
    } catch (e) {
      setLocalError(message(e, 'Failed to start the warm-up'))
    }
  }

  const selectExercise = async (card: SuggestionCard) => {
    if (!picker) return
    const position = picker.kind === 'anchor' ? 1 : picker.position
    setLocalError(null)
    try {
      await addEntry(picker.roundId, card.exercise_id, position)
    } catch (e) {
      setLocalError(message(e, 'Failed to add the exercise'))
      return
    }
    if (picker.kind === 'anchor') {
      setPicker({
        kind: 'partner',
        roundId: picker.roundId,
        anchorExerciseId: card.exercise_id,
        position: 2,
      })
    } else {
      setPicker(null)
    }
    setAnchorData(null)
    setPartnerData(null)
  }

  const finish = async () => {
    setLocalError(null)
    try {
      await complete()
      setFinished(true)
    } catch (e) {
      setLocalError(message(e, 'Failed to finish the session'))
    }
  }

  const handleDiscard = async () => {
    if (!window.confirm('Discard this session? Everything logged will be lost.')) return
    setLocalError(null)
    try {
      await discard()
      navigate('/')
    } catch (e) {
      setLocalError(message(e, 'Failed to discard the session'))
    }
  }

  const addStaple = async (exerciseId: number) => {
    setLocalError(null)
    setStapling(exerciseId)
    try {
      await createStaple(exerciseId)
      setStaples(await listStaples())
    } catch (e) {
      setLocalError(message(e, 'Failed to add to staples'))
    } finally {
      setStapling(null)
    }
  }

  if (finished) {
    const stapleIds = new Set(staples.map((s) => s.exercise_id))
    const seen = new Set<number>()
    const newExercises = session.rounds
      .flatMap((r) => r.entries)
      .filter((e) => {
        if (stapleIds.has(e.exercise_id) || seen.has(e.exercise_id)) return false
        seen.add(e.exercise_id)
        return true
      })

    return (
      <div className="container mx-auto p-6 max-w-2xl">
        <h1 className="text-2xl font-bold mb-4">Session Complete</h1>
        {localError && <div className="text-red-600 mb-4">{localError}</div>}
        <CoverageChips coverage={coverage} />

        <div className="bg-white rounded-lg border p-4">
          {session.rounds.map((r) => (
            <div key={r.id} className="mb-2">
              <span className="text-sm text-gray-400 mr-2">Round {r.order}:</span>
              {r.entries.length > 0
                ? r.entries.map((e) => `${e.exercise_name} (${e.sets.length} sets)`).join(' + ')
                : 'no exercises'}
            </div>
          ))}
          {session.rounds.length === 0 && <p className="text-gray-500">No rounds logged.</p>}
        </div>

        {staplesError && (
          <div className="bg-gray-50 border rounded-lg p-4 mt-4 text-sm text-gray-600">
            {staplesError} Add-to-staples is unavailable right now &mdash; you can add them from the
            staples list later.
          </div>
        )}

        {staplesLoaded && !staplesError && newExercises.length > 0 && (
          <div
            className="bg-purple-50 border border-purple-200 rounded-lg p-4 mt-4"
            data-testid="add-staples"
          >
            <h3 className="font-semibold mb-2">New exercises this session</h3>
            <p className="text-sm text-gray-600 mb-2">
              Add any you want offered as an anchor next time.
            </p>
            {newExercises.map((e) => (
              <div key={e.id} className="flex justify-between items-center py-1 gap-2">
                <span>{e.exercise_name}</span>
                <button
                  onClick={() => addStaple(e.exercise_id)}
                  disabled={stapling !== null}
                  className="text-sm bg-purple-600 text-white px-4 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                >
                  Add to staples
                </button>
              </div>
            ))}
          </div>
        )}

        <button
          onClick={() => navigate('/')}
          className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md"
        >
          Back to Day Plans
        </button>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 max-w-2xl">
      <div className="flex justify-between items-center mb-4 gap-2">
        <h1 className="text-2xl font-bold">Active Session</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={finish}
            disabled={busy}
            className="bg-green-600 text-white px-4 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Finish Session
          </button>
          <button
            onClick={handleDiscard}
            disabled={busy}
            className="text-red-500 px-3 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Discard
          </button>
        </div>
      </div>

      {error && <div className="text-red-600 mb-4">{error}</div>}
      {localError && <div className="text-red-600 mb-4">{localError}</div>}

      <CoverageChips coverage={coverage} />

      {session.rounds.length === 0 && warmupError && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 text-sm text-gray-700">
          {warmupError} Warm up with whatever is free, then start your first round below.
        </div>
      )}

      {session.rounds.length === 0 && warmups.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4" data-testid="warmup-card">
          <h3 className="font-semibold mb-2">Warm-up &mdash; what&apos;s available?</h3>
          {warmups.map((w, i) => (
            <button
              key={w.id}
              onClick={() => startWarmup(w.id)}
              disabled={busy}
              className={`block w-full text-left rounded-md px-3 py-3 mb-1 disabled:opacity-50 disabled:cursor-not-allowed ${
                i === 0 ? 'bg-white border-2 border-blue-400 font-medium' : 'bg-white border'
              }`}
            >
              {w.name} {i === 0 && <span className="text-xs text-blue-600">(preferred)</span>}
            </button>
          ))}
        </div>
      )}

      {session.rounds.map((round) => (
        <div key={round.id} className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <h2 className="font-semibold text-gray-700">Round {round.order}</h2>
            {round.entries.length > 0 && round.entries.length < 3 && (
              <button
                onClick={() =>
                  setPicker({
                    kind: 'partner',
                    roundId: round.id,
                    anchorExerciseId: round.entries[0].exercise_id,
                    position: (round.entries.length + 1) as 2 | 3,
                  })
                }
                disabled={busy}
                className="text-sm text-blue-600 px-2 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                + Add exercise #{round.entries.length + 1}
              </button>
            )}
          </div>
          {round.entries.map((entry) => (
            <EntryCard
              key={entry.id}
              entry={entry}
              onLogSet={handleLogSet}
              busy={busy}
              error={entryError?.entryId === entry.id ? entryError.message : null}
            />
          ))}
          {/* An empty round is reachable by cancelling the anchor picker, so it
              must always carry its own control to re-open that picker —
              otherwise the round is stranded and unfillable. */}
          {round.entries.length === 0 && (
            <button
              onClick={() => setPicker({ kind: 'anchor', roundId: round.id })}
              disabled={busy}
              className="w-full border-2 border-dashed rounded-lg py-4 text-gray-600 hover:border-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              + Pick an anchor for this round
            </button>
          )}
        </div>
      ))}

      {picker && (
        <div className="bg-gray-50 border rounded-lg p-4 mb-4" data-testid="picker">
          <h3 className="font-semibold mb-3">
            {picker.kind === 'anchor'
              ? "What's free? Pick your anchor"
              : `Partner suggestion (#${picker.position})`}
          </h3>

          {suggestionError && <div className="text-red-600 mb-2 text-sm">{suggestionError}</div>}

          {picker.kind === 'anchor' && (
            <>
              {!anchorData && !suggestionError && (
                <p className="text-sm text-gray-500">Loading suggestions...</p>
              )}
              {/* Anchor suggestions are drawn exclusively from the staple pool,
                  and a brand-new user's pool is empty. Without this the picker
                  renders a heading, nothing, and Cancel -- a dead end with no
                  hint that staples are the missing input. */}
              {anchorData && anchorCardCount === 0 && (
                <div
                  className="bg-white border rounded-lg p-4 text-sm text-gray-700"
                  data-testid="anchor-empty"
                >
                  <p className="font-medium mb-1">No anchor suggestions yet.</p>
                  <p className="mb-2">
                    Anchors are drawn from your staple pool &mdash; the exercises you have marked as
                    ones you actually do.{' '}
                    {anchorData.not_recommended.length > 0
                      ? 'Everything in it was filtered out for this round; see the reasons below.'
                      : 'It is currently empty.'}
                  </p>
                  <Link to="/exercises" className="text-blue-600 underline">
                    Browse exercises and add a few staples
                  </Link>
                  <span>, then come back and start this round.</span>
                </div>
              )}
              {anchorData?.groups.map((group) => (
                <div key={group.pattern.id} className="mb-3">
                  <div className="text-sm text-gray-500 mb-1">
                    {group.pattern.name} {group.covered && '(covered)'}
                  </div>
                  {group.staples.length > 0 ? (
                    <SuggestionList
                      cards={group.staples}
                      notRecommended={[]}
                      onSelect={selectExercise}
                      disabled={busy}
                    />
                  ) : (
                    <p className="text-sm text-gray-400">No staples for this pattern yet.</p>
                  )}
                </div>
              ))}
              {anchorData && (
                <SuggestionList
                  cards={[]}
                  notRecommended={anchorData.not_recommended}
                  onSelect={selectExercise}
                  disabled={busy}
                />
              )}
            </>
          )}

          {picker.kind === 'partner' && (
            <>
              {!partnerData && !suggestionError && (
                <p className="text-sm text-gray-500">Loading suggestions...</p>
              )}
              {partnerData && (
                <SuggestionList
                  cards={partnerData.candidates}
                  novelty={partnerData.novelty}
                  notRecommended={partnerData.not_recommended}
                  onSelect={selectExercise}
                  disabled={busy}
                />
              )}
              {partnerData &&
                partnerData.candidates.length === 0 &&
                !partnerData.novelty && (
                  <p className="text-sm text-gray-500">
                    No partner suggestions available &mdash; skip this one and keep going.
                  </p>
                )}
            </>
          )}

          <button onClick={() => setPicker(null)} className="text-sm text-gray-500 mt-2 px-2 py-2">
            Cancel
          </button>
        </div>
      )}

      {!picker && (
        <button
          onClick={startRound}
          disabled={busy}
          className="w-full border-2 border-dashed rounded-lg py-4 text-gray-600 hover:border-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          + Start Round {session.rounds.length + 1}
        </button>
      )}
    </div>
  )
}
