import { useEffect, useState } from 'react'
import { exerciseApi, type Exercise, type ExerciseCreate, type ExerciseUpdate, type MuscleGroupAssignment } from '../services/exercises'
import { equipmentApi } from '../services/equipment'
import { muscleGroupApi } from '../services/muscleGroups'
import { useUIStore } from '../stores/uiStore'
import type { Equipment, MuscleGroup } from '../services/api'

interface ExerciseFormModalProps {
  exercise: Exercise | null // null = create mode
  onClose: () => void
  onSaved: () => void
}

interface MuscleGroupRow {
  muscle_group_id: number | null
  role: 'target' | 'secondary' | 'tertiary'
}

function ExerciseFormModal({ exercise, onClose, onSaved }: ExerciseFormModalProps) {
  const { showToast } = useUIStore()
  const isEdit = exercise !== null

  // Reference data
  const [equipmentList, setEquipmentList] = useState<Equipment[]>([])
  const [muscleGroupList, setMuscleGroupList] = useState<MuscleGroup[]>([])
  const [loadingData, setLoadingData] = useState(true)

  // Form state - Basic
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [difficulty, setDifficulty] = useState<string>('')
  const [exerciseClassification, setExerciseClassification] = useState('')

  // Equipment
  const [primaryEquipmentId, setPrimaryEquipmentId] = useState<number | null>(null)
  const [secondaryEquipmentId, setSecondaryEquipmentId] = useState<number | null>(null)

  // Muscle groups
  const [muscleGroupRows, setMuscleGroupRows] = useState<MuscleGroupRow[]>([
    { muscle_group_id: null, role: 'target' },
  ])

  // Classification
  const [bodyRegion, setBodyRegion] = useState('')
  const [forceType, setForceType] = useState('')
  const [mechanics, setMechanics] = useState('')
  const [laterality, setLaterality] = useState('')

  // Advanced (collapsible)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [posture, setPosture] = useState('')
  const [movementPattern1, setMovementPattern1] = useState('')
  const [movementPattern2, setMovementPattern2] = useState('')
  const [movementPattern3, setMovementPattern3] = useState('')
  const [instructions, setInstructions] = useState('')
  const [shortDemoUrl, setShortDemoUrl] = useState('')
  const [inDepthUrl, setInDepthUrl] = useState('')

  // Defaults
  const [defaultSets, setDefaultSets] = useState<string>('')
  const [defaultReps, setDefaultReps] = useState<string>('')
  const [defaultWeight, setDefaultWeight] = useState<string>('')

  // UI state
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load reference data
  useEffect(() => {
    const load = async () => {
      try {
        const [equip, mgs] = await Promise.all([
          equipmentApi.list(),
          muscleGroupApi.list(),
        ])
        setEquipmentList(equip)
        setMuscleGroupList(mgs)
      } catch (err) {
        console.error('Failed to load reference data:', err)
      } finally {
        setLoadingData(false)
      }
    }
    load()
  }, [])

  // Populate form when editing
  useEffect(() => {
    if (!exercise) return
    setName(exercise.name)
    setDescription(exercise.description || '')
    setDifficulty(exercise.difficulty || '')
    setExerciseClassification(exercise.exercise_classification || '')
    setPrimaryEquipmentId(exercise.primary_equipment?.id ?? null)
    setSecondaryEquipmentId(exercise.secondary_equipment?.id ?? null)
    setBodyRegion(exercise.body_region || '')
    setForceType(exercise.force_type || '')
    setMechanics(exercise.mechanics || '')
    setLaterality(exercise.laterality || '')
    setPosture(exercise.posture || '')
    setMovementPattern1(exercise.movement_pattern_1 || '')
    setMovementPattern2(exercise.movement_pattern_2 || '')
    setMovementPattern3(exercise.movement_pattern_3 || '')
    setInstructions('')
    setShortDemoUrl(exercise.short_demo_url || '')
    setInDepthUrl(exercise.in_depth_url || '')
    setDefaultSets(exercise.default_sets?.toString() || '')
    setDefaultReps(exercise.default_reps?.toString() || '')
    setDefaultWeight(exercise.default_weight?.toString() || '')

    // Populate muscle group rows from exercise data
    // We don't have role info from the response schema, so default existing to "target"
    if (exercise.muscle_groups.length > 0) {
      setMuscleGroupRows(
        exercise.muscle_groups.map((mg) => ({
          muscle_group_id: mg.id,
          role: 'target' as const, // API response doesn't include role; default to target
        }))
      )
    }
  }, [exercise])

  const handleAddMuscleGroup = () => {
    setMuscleGroupRows((prev) => [...prev, { muscle_group_id: null, role: 'target' }])
  }

  const handleRemoveMuscleGroup = (index: number) => {
    setMuscleGroupRows((prev) => prev.filter((_, i) => i !== index))
  }

  const handleMuscleGroupChange = (index: number, field: keyof MuscleGroupRow, value: number | string | null) => {
    setMuscleGroupRows((prev) =>
      prev.map((row, i) => (i === index ? { ...row, [field]: value } : row))
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Name is required')
      return
    }

    const muscleGroups: MuscleGroupAssignment[] = muscleGroupRows
      .filter((row) => row.muscle_group_id !== null)
      .map((row) => ({
        muscle_group_id: row.muscle_group_id as number,
        role: row.role,
      }))

    setSaving(true)
    try {
      if (isEdit) {
        const data: ExerciseUpdate = {
          name: name.trim(),
          description: description || null,
          difficulty: (difficulty as ExerciseUpdate['difficulty']) || null,
          exercise_classification: exerciseClassification || null,
          primary_equipment_id: primaryEquipmentId,
          secondary_equipment_id: secondaryEquipmentId,
          body_region: bodyRegion || null,
          force_type: forceType || null,
          mechanics: mechanics || null,
          laterality: laterality || null,
          posture: posture || null,
          movement_pattern_1: movementPattern1 || null,
          movement_pattern_2: movementPattern2 || null,
          movement_pattern_3: movementPattern3 || null,
          short_demo_url: shortDemoUrl || null,
          in_depth_url: inDepthUrl || null,
          instructions: instructions || null,
          muscle_groups: muscleGroups,
          default_sets: defaultSets ? parseInt(defaultSets) : null,
          default_reps: defaultReps ? parseInt(defaultReps) : null,
          default_weight: defaultWeight ? parseFloat(defaultWeight) : null,
        }
        await exerciseApi.update(exercise!.id, data)
        showToast('success', 'Exercise updated')
      } else {
        const data: ExerciseCreate = {
          name: name.trim(),
          description: description || undefined,
          difficulty: (difficulty as ExerciseCreate['difficulty']) || undefined,
          exercise_classification: exerciseClassification || undefined,
          primary_equipment_id: primaryEquipmentId,
          secondary_equipment_id: secondaryEquipmentId,
          body_region: bodyRegion || undefined,
          force_type: forceType || undefined,
          mechanics: mechanics || undefined,
          laterality: laterality || undefined,
          posture: posture || undefined,
          movement_pattern_1: movementPattern1 || undefined,
          movement_pattern_2: movementPattern2 || undefined,
          movement_pattern_3: movementPattern3 || undefined,
          short_demo_url: shortDemoUrl || undefined,
          in_depth_url: inDepthUrl || undefined,
          instructions: instructions || undefined,
          muscle_groups: muscleGroups.length > 0 ? muscleGroups : undefined,
          default_sets: defaultSets ? parseInt(defaultSets) : undefined,
          default_reps: defaultReps ? parseInt(defaultReps) : undefined,
          default_weight: defaultWeight ? parseFloat(defaultWeight) : undefined,
        }
        await exerciseApi.create(data)
        showToast('success', 'Exercise created')
      }
      onSaved()
      onClose()
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error).message ||
        'Failed to save exercise'
      setError(message)
    } finally {
      setSaving(false)
    }
  }

  if (loadingData) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
          <div className="text-gray-600">Loading...</div>
        </div>
      </div>
    )
  }

  const levelOneMuscleGroups = muscleGroupList.filter((mg) => mg.level === 1)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {isEdit ? 'Edit Exercise' : 'Create Exercise'}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          <div className="px-6 py-4 space-y-5">
            {error && (
              <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">{error}</div>
            )}

            {/* Basic Info */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Basic Info</h3>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., Barbell Bench Press"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Difficulty</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">--</option>
                    <option value="Easy">Easy</option>
                    <option value="Intermediate">Intermediate</option>
                    <option value="Advanced">Advanced</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Classification</label>
                  <input
                    type="text"
                    value={exerciseClassification}
                    onChange={(e) => setExerciseClassification(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Bodybuilding"
                  />
                </div>
              </div>
            </div>

            {/* Equipment */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Equipment</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Primary Equipment</label>
                  <select
                    value={primaryEquipmentId ?? ''}
                    onChange={(e) => setPrimaryEquipmentId(e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">None (Bodyweight)</option>
                    {equipmentList.map((eq) => (
                      <option key={eq.id} value={eq.id}>{eq.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Secondary Equipment</label>
                  <select
                    value={secondaryEquipmentId ?? ''}
                    onChange={(e) => setSecondaryEquipmentId(e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">None</option>
                    {equipmentList.map((eq) => (
                      <option key={eq.id} value={eq.id}>{eq.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Muscle Groups */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Muscle Groups</h3>
              {muscleGroupRows.map((row, index) => (
                <div key={index} className="flex gap-2 items-center">
                  <select
                    value={row.muscle_group_id ?? ''}
                    onChange={(e) =>
                      handleMuscleGroupChange(index, 'muscle_group_id', e.target.value ? parseInt(e.target.value) : null)
                    }
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select muscle group</option>
                    {levelOneMuscleGroups.map((mg) => (
                      <option key={mg.id} value={mg.id}>{mg.name}</option>
                    ))}
                  </select>
                  <select
                    value={row.role}
                    onChange={(e) => handleMuscleGroupChange(index, 'role', e.target.value)}
                    className="w-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="target">Target</option>
                    <option value="secondary">Secondary</option>
                    <option value="tertiary">Tertiary</option>
                  </select>
                  <button
                    type="button"
                    onClick={() => handleRemoveMuscleGroup(index)}
                    className="px-2 py-2 text-red-500 hover:text-red-700"
                    title="Remove"
                  >
                    &times;
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={handleAddMuscleGroup}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                + Add Muscle Group
              </button>
            </div>

            {/* Classification */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Movement Properties</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Body Region</label>
                  <select
                    value={bodyRegion}
                    onChange={(e) => setBodyRegion(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">--</option>
                    <option value="Upper Body">Upper Body</option>
                    <option value="Lower Body">Lower Body</option>
                    <option value="Core">Core</option>
                    <option value="Full Body">Full Body</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Force Type</label>
                  <select
                    value={forceType}
                    onChange={(e) => setForceType(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">--</option>
                    <option value="Push">Push</option>
                    <option value="Pull">Pull</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Mechanics</label>
                  <select
                    value={mechanics}
                    onChange={(e) => setMechanics(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">--</option>
                    <option value="Compound">Compound</option>
                    <option value="Isolation">Isolation</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Laterality</label>
                  <select
                    value={laterality}
                    onChange={(e) => setLaterality(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">--</option>
                    <option value="Bilateral">Bilateral</option>
                    <option value="Unilateral">Unilateral</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Defaults */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Defaults</h3>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Sets</label>
                  <input
                    type="number"
                    value={defaultSets}
                    onChange={(e) => setDefaultSets(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min="1"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Reps</label>
                  <input
                    type="number"
                    value={defaultReps}
                    onChange={(e) => setDefaultReps(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min="1"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Weight</label>
                  <input
                    type="number"
                    value={defaultWeight}
                    onChange={(e) => setDefaultWeight(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min="0"
                    step="0.5"
                  />
                </div>
              </div>
            </div>

            {/* Advanced (collapsible) */}
            <div>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
              >
                <span className={`transform transition-transform ${showAdvanced ? 'rotate-90' : ''}`}>
                  &#9654;
                </span>
                Advanced
              </button>
              {showAdvanced && (
                <div className="mt-3 space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Posture</label>
                    <input
                      type="text"
                      value={posture}
                      onChange={(e) => setPosture(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., Standing, Supine, Prone"
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Movement 1</label>
                      <input
                        type="text"
                        value={movementPattern1}
                        onChange={(e) => setMovementPattern1(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Movement 2</label>
                      <input
                        type="text"
                        value={movementPattern2}
                        onChange={(e) => setMovementPattern2(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Movement 3</label>
                      <input
                        type="text"
                        value={movementPattern3}
                        onChange={(e) => setMovementPattern3(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Instructions</label>
                    <textarea
                      value={instructions}
                      onChange={(e) => setInstructions(e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Demo URL</label>
                      <input
                        type="url"
                        value={shortDemoUrl}
                        onChange={(e) => setShortDemoUrl(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">In-Depth URL</label>
                      <input
                        type="url"
                        value={inDepthUrl}
                        onChange={(e) => setInDepthUrl(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving...' : isEdit ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ExerciseFormModal
