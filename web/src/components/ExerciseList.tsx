/**
 * Exercise List Component
 * Displays filtered exercises for a slot with sorting and filtering
 */
import { useState, useMemo } from 'react'
import { Exercise } from '../services/exercises'

interface ExerciseListProps {
  exercises: Exercise[]
  muscleGroupIds: number[]
  selectedExerciseId?: number | null
  onSelectExercise?: (exerciseId: number) => void
  onCreateVariant?: (exercise: Exercise) => void
}

type SortField = 'name' | 'difficulty' | 'last_performed' | 'equipment'
type SortOrder = 'asc' | 'desc'

export default function ExerciseList({ 
  exercises, 
  muscleGroupIds, 
  selectedExerciseId,
  onSelectExercise,
  onCreateVariant
}: ExerciseListProps) {
  const [sortBy, setSortBy] = useState<SortField>('name')
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')
  const [filterDifficulty, setFilterDifficulty] = useState<string>('')
  const [filterEquipment, setFilterEquipment] = useState<string>('')
  const [filterBodyRegion, setFilterBodyRegion] = useState<string>('')
  const [filterMechanics, setFilterMechanics] = useState<string>('')

  // Get unique filter values from exercises
  const uniqueDifficulties = useMemo(() => {
    const difficulties = exercises
      .map(e => e.difficulty)
      .filter((d): d is string => d !== null)
    return Array.from(new Set(difficulties)).sort()
  }, [exercises])

  const uniqueEquipment = useMemo(() => {
    const equipment = new Set<string>()
    exercises.forEach(e => {
      if (e.primary_equipment) equipment.add(e.primary_equipment.name)
      if (e.secondary_equipment) equipment.add(e.secondary_equipment.name)
    })
    return Array.from(equipment).sort()
  }, [exercises])

  const uniqueBodyRegions = useMemo(() => {
    const regions = exercises
      .map(e => e.body_region)
      .filter((r): r is string => r !== null)
    return Array.from(new Set(regions)).sort()
  }, [exercises])

  const uniqueMechanics = useMemo(() => {
    const mechanics = exercises
      .map(e => e.mechanics)
      .filter((m): m is string => m !== null)
    return Array.from(new Set(mechanics)).sort()
  }, [exercises])

  // Filter and sort exercises
  const filteredAndSortedExercises = useMemo(() => {
    let filtered = [...exercises]

    // Apply filters
    if (filterDifficulty) {
      filtered = filtered.filter(e => e.difficulty === filterDifficulty)
    }
    if (filterEquipment) {
      filtered = filtered.filter(e => 
        e.primary_equipment?.name === filterEquipment || 
        e.secondary_equipment?.name === filterEquipment
      )
    }
    if (filterBodyRegion) {
      filtered = filtered.filter(e => e.body_region === filterBodyRegion)
    }
    if (filterMechanics) {
      filtered = filtered.filter(e => e.mechanics === filterMechanics)
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let comparison = 0

      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name)
          break
        case 'difficulty':
          const difficultyOrder = ['Beginner', 'Novice', 'Intermediate', 'Advanced', 'Expert']
          const aDiff = a.difficulty ? difficultyOrder.indexOf(a.difficulty) : -1
          const bDiff = b.difficulty ? difficultyOrder.indexOf(b.difficulty) : -1
          comparison = aDiff - bDiff
          break
        case 'last_performed':
          const aDate = a.last_performed ? new Date(a.last_performed).getTime() : 0
          const bDate = b.last_performed ? new Date(b.last_performed).getTime() : 0
          comparison = aDate - bDate
          // Nulls last
          if (!a.last_performed && b.last_performed) comparison = 1
          if (a.last_performed && !b.last_performed) comparison = -1
          break
        case 'equipment':
          const aEq = a.primary_equipment?.name || ''
          const bEq = b.primary_equipment?.name || ''
          comparison = aEq.localeCompare(bEq)
          break
      }

      return sortOrder === 'asc' ? comparison : -comparison
    })

    return filtered
  }, [exercises, sortBy, sortOrder, filterDifficulty, filterEquipment, filterBodyRegion, filterMechanics])

  const formatLastPerformed = (dateStr: string | null) => {
    if (!dateStr) return 'Never'
    const date = new Date(dateStr)
    const now = new Date()
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`
    return `${Math.floor(diffDays / 365)} years ago`
  }

  if (exercises.length === 0) {
    return (
      <div className="text-center py-4 text-gray-500 text-sm">
        No exercises found for selected muscle groups
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Sorting and Filtering Controls */}
      <div className="bg-gray-50 rounded-md p-3 space-y-3">
        {/* Sort Controls */}
        <div className="flex flex-wrap gap-3 items-center">
          <label className="text-xs font-medium text-gray-700">Sort by:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortField)}
            className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="name">Name</option>
            <option value="difficulty">Difficulty</option>
            <option value="last_performed">Last Performed</option>
            <option value="equipment">Equipment</option>
          </select>
          <button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            className="text-xs px-2 py-1 bg-white border border-gray-300 rounded hover:bg-gray-50"
            title={`Sort ${sortOrder === 'asc' ? 'Ascending' : 'Descending'}`}
          >
            {sortOrder === 'asc' ? '↑' : '↓'}
          </button>
        </div>

        {/* Filter Controls */}
        <div className="grid grid-cols-2 gap-2">
          {uniqueDifficulties.length > 0 && (
            <div>
              <label className="text-xs font-medium text-gray-700 block mb-1">Difficulty:</label>
              <select
                value={filterDifficulty}
                onChange={(e) => setFilterDifficulty(e.target.value)}
                className="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All</option>
                {uniqueDifficulties.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          )}
          {uniqueEquipment.length > 0 && (
            <div>
              <label className="text-xs font-medium text-gray-700 block mb-1">Equipment:</label>
              <select
                value={filterEquipment}
                onChange={(e) => setFilterEquipment(e.target.value)}
                className="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All</option>
                {uniqueEquipment.map(eq => (
                  <option key={eq} value={eq}>{eq}</option>
                ))}
              </select>
            </div>
          )}
          {uniqueBodyRegions.length > 0 && (
            <div>
              <label className="text-xs font-medium text-gray-700 block mb-1">Body Region:</label>
              <select
                value={filterBodyRegion}
                onChange={(e) => setFilterBodyRegion(e.target.value)}
                className="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All</option>
                {uniqueBodyRegions.map(region => (
                  <option key={region} value={region}>{region}</option>
                ))}
              </select>
            </div>
          )}
          {uniqueMechanics.length > 0 && (
            <div>
              <label className="text-xs font-medium text-gray-700 block mb-1">Mechanics:</label>
              <select
                value={filterMechanics}
                onChange={(e) => setFilterMechanics(e.target.value)}
                className="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All</option>
                {uniqueMechanics.map(mech => (
                  <option key={mech} value={mech}>{mech}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Active Filters Summary */}
        {(filterDifficulty || filterEquipment || filterBodyRegion || filterMechanics) && (
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-xs text-gray-600">Active filters:</span>
            {filterDifficulty && (
              <button
                onClick={() => setFilterDifficulty('')}
                className="text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
              >
                Difficulty: {filterDifficulty} ×
              </button>
            )}
            {filterEquipment && (
              <button
                onClick={() => setFilterEquipment('')}
                className="text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
              >
                Equipment: {filterEquipment} ×
              </button>
            )}
            {filterBodyRegion && (
              <button
                onClick={() => setFilterBodyRegion('')}
                className="text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
              >
                Region: {filterBodyRegion} ×
              </button>
            )}
            {filterMechanics && (
              <button
                onClick={() => setFilterMechanics('')}
                className="text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
              >
                Mechanics: {filterMechanics} ×
              </button>
            )}
            <button
              onClick={() => {
                setFilterDifficulty('')
                setFilterEquipment('')
                setFilterBodyRegion('')
                setFilterMechanics('')
              }}
              className="text-xs px-2 py-0.5 text-red-600 hover:text-red-800"
            >
              Clear all
            </button>
          </div>
        )}

        {/* Results count */}
        <div className="text-xs text-gray-600">
          Showing {filteredAndSortedExercises.length} of {exercises.length} exercises
        </div>
      </div>

      {/* Exercise List */}
      <div className="max-h-96 overflow-y-auto border border-gray-300 rounded-md">
        <div className="divide-y">
          {filteredAndSortedExercises.map((exercise) => {
            const isSelected = selectedExerciseId === exercise.id
            return (
              <div 
                key={exercise.id} 
                className={`p-3 cursor-pointer transition-colors ${
                  isSelected 
                    ? 'bg-blue-50 border-l-4 border-blue-600' 
                    : 'hover:bg-gray-50'
                }`}
                onClick={() => onSelectExercise?.(exercise.id)}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className={`font-medium text-sm ${isSelected ? 'text-blue-900' : ''}`}>
                        {exercise.name}
                      </h4>
                      {exercise.is_custom && (
                        <span className="text-xs px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded font-medium">
                          Custom
                        </span>
                      )}
                      {exercise.variant_type && (
                        <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded font-medium">
                          {exercise.variant_type}
                        </span>
                      )}
                      {isSelected && (
                        <span className="text-xs text-blue-600 font-semibold">✓ Selected</span>
                      )}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-600">
                      {exercise.difficulty && (
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded">
                          {exercise.difficulty}
                        </span>
                      )}
                      {exercise.primary_equipment && (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded">
                          {exercise.primary_equipment.name}
                        </span>
                      )}
                      {exercise.body_region && (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded">
                          {exercise.body_region}
                        </span>
                      )}
                      {exercise.mechanics && (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded">
                          {exercise.mechanics}
                        </span>
                      )}
                      {exercise.last_performed && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-800 rounded" title={new Date(exercise.last_performed).toLocaleString()}>
                          Last: {formatLastPerformed(exercise.last_performed)}
                        </span>
                      )}
                      {/* Show variant defaults if available */}
                      {(exercise.default_sets || exercise.default_reps || exercise.default_weight) && (
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded" title="Default parameters for this variant">
                          Default: {exercise.default_sets && `${exercise.default_sets}×`}{exercise.default_reps && exercise.default_reps}{exercise.default_weight && `@${exercise.default_weight}lbs`}
                        </span>
                      )}
                    </div>
                    <div className="mt-2 flex items-center gap-3">
                      {exercise.short_demo_url && (
                        <a
                          href={exercise.short_demo_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          Watch Demo →
                        </a>
                      )}
                      {onCreateVariant && !exercise.is_custom && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            onCreateVariant(exercise)
                          }}
                          className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                          title="Create a variant for different workout styles (e.g., HIIT, Strength)"
                        >
                          Create Variant
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
