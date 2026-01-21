/**
 * TagDisplay component - displays tags with optional remove functionality
 */
import { type Tag } from '../services/tags'

interface TagDisplayProps {
  tags: Tag[]
  onRemove?: (tagId: number) => void
  size?: 'sm' | 'md' | 'lg'
  showCategory?: boolean
}

export function TagDisplay({ tags, onRemove, size = 'md', showCategory = false }: TagDisplayProps) {
  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2 py-1',
    lg: 'text-base px-3 py-1.5',
  }

  if (tags.length === 0) {
    return null
  }

  return (
    <div className="flex flex-wrap gap-2">
      {tags.map((tag) => (
        <span
          key={tag.id}
          className={`inline-flex items-center gap-1 bg-gray-100 text-gray-800 rounded-md ${sizeClasses[size]}`}
        >
          {tag.name}
          {showCategory && tag.category && (
            <span className="text-gray-500 text-xs">({tag.category})</span>
          )}
          {onRemove && (
            <button
              type="button"
              onClick={() => onRemove(tag.id)}
              className="hover:text-gray-900 focus:outline-none ml-1"
              aria-label={`Remove ${tag.name}`}
            >
              ×
            </button>
          )}
        </span>
      ))}
    </div>
  )
}
