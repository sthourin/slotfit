/**
 * Tappable list of exercise suggestion cards (anchors, partners, novelty),
 * with an expandable "why not others?" explanation list.
 *
 * Every card is a real <button> whose accessible name contains the exercise
 * name, so it can be reached one-handed and by assistive tech.
 */
import { useState } from 'react'
import type { SuggestionCard, NotRecommendedEntry } from '../../services/suggestions'

interface Props {
  cards: SuggestionCard[]
  novelty?: SuggestionCard | null
  notRecommended: NotRecommendedEntry[]
  onSelect: (card: SuggestionCard) => void
  disabled?: boolean
}

/**
 * Second line of a card: equipment, then history, then the progression target.
 * `target` is null when the exercise has no history, and `target.weight` is
 * null for bodyweight work — neither may render as "null" or "0".
 *
 * The target clause is driven by `reps_goal`: time-only work carries none and
 * so prescribes nothing, rather than rendering an invented rep count for a
 * rowing machine.
 */
function cardDetail(card: SuggestionCard): string {
  const parts: string[] = [card.is_bodyweight ? 'Bodyweight' : card.equipment_name ?? 'No equipment']

  if (card.target?.last_summary) {
    parts.push(`Last: ${card.target.last_summary}`)
  } else if (!card.last_performed) {
    parts.push('Never performed')
  }

  const target = card.target
  if (target) {
    const weight = target.weight != null ? ` @ ${target.weight}` : ''
    if (target.reps_goal === 'beat') {
      parts.push(`Beat ${target.reps}${weight}`)
    } else if (target.reps_goal === 'target') {
      parts.push(`Target: ${target.sets}x${target.reps}${weight}`)
    }
  }

  return parts.join(' · ')
}

export default function SuggestionList({ cards, novelty, notRecommended, onSelect, disabled }: Props) {
  const [showWhyNot, setShowWhyNot] = useState(false)

  return (
    <div>
      {cards.map((card) => (
        <button
          key={card.exercise_id}
          onClick={() => onSelect(card)}
          disabled={disabled}
          className="w-full text-left bg-white border rounded-lg p-3 mb-2 hover:border-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div className="font-medium">{card.exercise_name}</div>
          <div className="text-sm text-gray-500">{cardDetail(card)}</div>
        </button>
      ))}

      {novelty && (
        <button
          onClick={() => onSelect(novelty)}
          disabled={disabled}
          className="w-full text-left border-2 border-dashed border-purple-300 rounded-lg p-3 mb-2 hover:border-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div className="text-sm text-purple-600 font-medium">Try something new</div>
          <div className="font-medium">{novelty.exercise_name}</div>
          <div className="text-sm text-gray-500">{cardDetail(novelty)}</div>
        </button>
      )}

      {notRecommended.length > 0 && (
        <div className="mt-2">
          <button
            onClick={() => setShowWhyNot(!showWhyNot)}
            className="text-sm text-gray-500 underline py-2"
          >
            Why not others? ({notRecommended.length})
          </button>
          {showWhyNot && (
            <ul className="text-sm text-gray-500 mt-1 list-disc pl-5">
              {notRecommended.map((n, i) => (
                <li key={`${n.exercise_name}-${i}`}>
                  {n.exercise_name}: {n.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
