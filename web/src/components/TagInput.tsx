/**
 * TagInput component - allows creating tags on the fly and selecting from existing tags
 */
import { useState, useEffect, useRef } from 'react'
import { tagsService, type Tag } from '../services/tags'

interface TagInputProps {
  selectedTags: Tag[]
  onTagsChange: (tags: Tag[]) => void
  placeholder?: string
  category?: string // Optional category filter for suggestions
}

export function TagInput({ selectedTags, onTagsChange, placeholder = 'Add tags...', category }: TagInputProps) {
  const [inputValue, setInputValue] = useState('')
  const [suggestions, setSuggestions] = useState<Tag[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  // Fetch suggestions when input changes
  useEffect(() => {
    const fetchSuggestions = async () => {
      if (inputValue.length < 2) {
        setSuggestions([])
        setShowSuggestions(false)
        return
      }

      setIsLoading(true)
      try {
        const response = await tagsService.list({
          search: inputValue,
          category: category || undefined,
          limit: 10,
        })
        // Filter out already selected tags
        const filtered = response.tags.filter(
          (tag) => !selectedTags.some((selected) => selected.id === tag.id)
        )
        setSuggestions(filtered)
        setShowSuggestions(filtered.length > 0 || inputValue.length > 0)
      } catch (error) {
        console.error('Error fetching tag suggestions:', error)
        setSuggestions([])
      } finally {
        setIsLoading(false)
      }
    }

    const debounceTimer = setTimeout(fetchSuggestions, 300)
    return () => clearTimeout(debounceTimer)
  }, [inputValue, selectedTags, category])

  // Handle clicking outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value)
  }

  const handleInputKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      e.preventDefault()
      await createOrSelectTag(inputValue.trim())
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
      inputRef.current?.blur()
    } else if (e.key === 'ArrowDown' && suggestions.length > 0) {
      e.preventDefault()
      // Focus first suggestion (could be enhanced to navigate with arrow keys)
    }
  }

  const createOrSelectTag = async (tagName: string) => {
    // Check if tag already exists in suggestions
    const existingTag = suggestions.find(
      (tag) => tag.name.toLowerCase() === tagName.toLowerCase()
    )

    if (existingTag) {
      onTagsChange([...selectedTags, existingTag])
    } else {
      // Create new tag
      try {
        const newTag = await tagsService.create({
          name: tagName,
          category: category || null,
        })
        onTagsChange([...selectedTags, newTag])
      } catch (error) {
        console.error('Error creating tag:', error)
        // If creation fails, try to find it (might have been created by another request)
        try {
          const response = await tagsService.list({ search: tagName, limit: 1 })
          if (response.tags.length > 0) {
            const foundTag = response.tags[0]
            onTagsChange([...selectedTags, foundTag])
          }
        } catch (err) {
          console.error('Error finding tag:', err)
        }
      }
    }

    setInputValue('')
    setShowSuggestions(false)
  }

  const removeTag = (tagId: number) => {
    onTagsChange(selectedTags.filter((tag) => tag.id !== tagId))
  }

  const selectSuggestion = (tag: Tag) => {
    onTagsChange([...selectedTags, tag])
    setInputValue('')
    setShowSuggestions(false)
  }

  return (
    <div className="relative">
      <div className="flex flex-wrap gap-2 p-2 border border-gray-300 rounded-md min-h-[42px] focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500">
        {/* Selected tags */}
        {selectedTags.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-sm"
          >
            {tag.name}
            <button
              type="button"
              onClick={() => removeTag(tag.id)}
              className="hover:text-blue-900 focus:outline-none"
              aria-label={`Remove ${tag.name}`}
            >
              ×
            </button>
          </span>
        ))}

        {/* Input */}
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleInputKeyDown}
          onFocus={() => {
            if (suggestions.length > 0 || inputValue.length > 0) {
              setShowSuggestions(true)
            }
          }}
          placeholder={selectedTags.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[120px] outline-none border-none bg-transparent"
        />
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && (
        <div
          ref={suggestionsRef}
          className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto"
        >
          {isLoading ? (
            <div className="px-4 py-2 text-sm text-gray-500">Loading...</div>
          ) : suggestions.length > 0 ? (
            <ul className="py-1">
              {suggestions.map((tag) => (
                <li
                  key={tag.id}
                  onClick={() => selectSuggestion(tag)}
                  className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                >
                  {tag.name}
                  {tag.category && (
                    <span className="ml-2 text-xs text-gray-500">({tag.category})</span>
                  )}
                </li>
              ))}
            </ul>
          ) : inputValue.trim() ? (
            <div
              onClick={() => createOrSelectTag(inputValue.trim())}
              className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm text-gray-600"
            >
              Create "{inputValue.trim()}"
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}
