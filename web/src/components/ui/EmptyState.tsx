/**
 * Empty State Component
 * Consistent empty state display with icon, message, and optional CTA
 */
import { Link } from 'react-router-dom'

export interface EmptyStateProps {
  icon?: string
  title: string
  description?: string
  action?: {
    label: string
    onClick?: () => void
    href?: string
  }
}

const defaultIcons: Record<string, string> = {
  workout: '🏋️',
  exercise: '💪',
  routine: '📋',
  record: '🏆',
  history: '📊',
  settings: '⚙️',
  search: '🔍',
  data: '📈',
}

export default function EmptyState({
  icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  // Try to infer icon from title if not provided
  const displayIcon =
    icon ||
    Object.entries(defaultIcons).find(([key]) =>
      title.toLowerCase().includes(key)
    )?.[1] ||
    '📭'

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div
        className="text-4xl mb-4"
        role="img"
        aria-hidden="true"
      >
        {displayIcon}
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-gray-500 max-w-sm mb-4">{description}</p>
      )}
      {action && (
        action.href ? (
          <Link
            to={action.href}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            {action.label}
          </Link>
        ) : (
          <button
            onClick={action.onClick}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            {action.label}
          </button>
        )
      )}
    </div>
  )
}
