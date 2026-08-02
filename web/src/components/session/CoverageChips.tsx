/**
 * Persistent pattern-coverage chips.
 *
 * Always visible during a session so the lifter can see, at a glance and
 * between sets, which movement patterns today still needs.
 */
import type { Coverage } from '../../services/sessions'

export default function CoverageChips({ coverage }: { coverage: Coverage | null }) {
  if (!coverage || coverage.goals.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2 mb-4" data-testid="coverage-chips">
      {coverage.goals.map((g) => (
        <span
          key={g.pattern_id}
          className={`px-3 py-1.5 rounded-full text-sm ${
            g.covered
              ? 'bg-green-100 text-green-800'
              : g.required
                ? 'bg-yellow-100 text-yellow-800'
                : 'bg-gray-100 text-gray-600'
          }`}
        >
          {g.name} {g.sets_done}/{g.target_sets}
          {!g.required && ' (optional)'}
        </span>
      ))}
    </div>
  )
}
